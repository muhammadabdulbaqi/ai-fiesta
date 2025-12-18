from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import os
from datetime import datetime
import uuid
from collections import defaultdict
import time
import json

from .. import schemas, models
from ..config import settings
from ..llm.factory import llm_factory
from ..utils.stream_emulation import emulate_stream_text

# Database Imports
from app.database import get_db
from app.services import user_service, chat_service, auth_service
from app.db_models import User

router = APIRouter(prefix="", tags=["Chat"])
security = HTTPBearer()

# Simple per-user spacing tracker (In-memory is fine for rate limiting for now)
user_last_request = defaultdict(float)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user from JWT token. Supports both regular users and admins."""
    from app.services import admin_service
    from app.db_models import Subscription
    from app import models
    import uuid
    from datetime import datetime
    
    token = credentials.credentials
    payload = auth_service.decode_access_token(token)
    
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    role = payload.get("role")
    
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # If admin, try to find a regular user account with the same email
    if role == "admin":
        admin = await admin_service.get_admin_by_id(db, user_id)
        if admin:
            # Look for a regular user with the same email
            user = await user_service.get_user_by_email(db, admin.email)
            if user:
                return user
            # If no regular user exists, create one automatically for the admin
            new_user = User(
                id=str(uuid.uuid4()),
                email=admin.email,
                username=admin.username,
                hashed_password=admin.hashed_password,
                is_active=True,
                created_at=datetime.now()
            )
            db.add(new_user)
            await db.flush()
            
            # Create default subscription
            tier = models.SUBSCRIPTION_TIERS["free"]
            subscription = Subscription(
                user_id=new_user.id,
                tier_id=tier["tier_id"],
                tier_name=tier["name"],
                plan_type="free",
                allowed_models=tier["allowed_models"],
                tokens_limit=tier["tokens_per_month"],
                tokens_used=0,
                tokens_remaining=tier["tokens_per_month"],
                credits_limit=tier["credits_per_month"],
                credits_used=0,
                credits_remaining=tier["credits_per_month"],
                monthly_cost_usd=tier.get("cost_usd", 0.0),
                monthly_api_cost_usd=0.0,
                rate_limit_per_minute=tier.get("rate_limit_per_minute", 5),
                status="active",
                created_at=datetime.now()
            )
            db.add(subscription)
            await db.commit()
            await db.refresh(new_user)
            return new_user
    
    # Regular user lookup
    user = await user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# --- Helper to safely stream an immediate error ---
def stream_error(code: str, message: str):
    """Returns a generator that yields a single error event."""
    payload = json.dumps({"type": "error", "error": code, "message": message})
    async def _gen():
        yield f"data: {payload}\n\n"
    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.post("/chat/", response_model=schemas.ChatResponse)
async def chat(
    request: schemas.ChatRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Chat endpoint with real LLMs and subscription management"""
    model = request.model or "mock"
    user_id = current_user.id
    
    # ---------------------------------------------------------
    # 1. VALIDATION & SETUP
    # ---------------------------------------------------------
    subscription = await user_service.get_subscription(db, user_id)
    if not subscription or subscription.status != "active":
        raise HTTPException(status_code=403, detail="Subscription inactive")
        
    if model not in subscription.allowed_models:
        raise HTTPException(status_code=403, detail=f"Model {model} not allowed")

    # ---------------------------------------------------------
    # 2. GENERATION
    # ---------------------------------------------------------
    provider = llm_factory.create_provider(model)
    estimated = provider.count_tokens(request.prompt)
    
    # Check credits logic (simplified check before generation)
    credits_needed = int((estimated + (request.max_tokens or 1000)) * models.MODEL_CREDIT_COSTS.get(model, 0.01))
    
    if subscription.credits_remaining < credits_needed:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    try:
        # Call LLM
        result = await provider.generate(
            prompt=request.prompt,
            model=model,
            max_tokens=request.max_tokens or 1000,
            temperature=request.temperature or 0.7,
        )

        content = result.get("content", str(result))
        model_used = result.get("model", model)
        prompt_tokens = result.get("prompt_tokens", 0)
        completion_tokens = result.get("completion_tokens", 0)
        total_tokens = result.get("total_tokens", prompt_tokens + completion_tokens)
        
        # ---------------------------------------------------------
        # 3. DEDUCTION & SAVING
        # ---------------------------------------------------------
        
        conv_id = request.conversation_id or str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        cost = 0.0
        if hasattr(provider, 'estimate_cost'):
            cost = provider.estimate_cost(prompt_tokens, completion_tokens, model_used)

        # DB Write
        multiplier = models.MODEL_CREDIT_COSTS.get(model_used, 0.01)
        credits_deducted = int(total_tokens * multiplier)
        
        # Atomic deduction
        updated_sub = await user_service.deduct_credits_atomic(db, user_id, credits_deducted)
        
        # Save user message first
        await chat_service.ensure_conversation(db, conv_id, user_id, title=request.prompt[:100] if request.prompt else None)
        await chat_service.save_message(
            db, conv_id, "user", request.prompt, None,
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            0.0
        )
        
        # Save assistant message
        await chat_service.save_message(
            db, conv_id, "assistant", content, model_used,
            {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens},
            cost
        )
        await chat_service.track_usage(db, user_id, provider.provider_name, model_used, prompt_tokens, completion_tokens, cost)
        
        return schemas.ChatResponse(
            message_id=message_id,
            conversation_id=conv_id,
            content=content,
            model=model_used,
            tokens_used=total_tokens,
            tokens_remaining=0, # Deprecated
            credits_used=updated_sub.credits_used,
            credits_remaining=updated_sub.credits_remaining
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream/chat")
async def stream_chat(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """HTTP SSE streaming endpoint."""
    try:
        data = await request.json()
    except Exception:
        return stream_error("invalid_request", "Expected JSON body")

    prompt = data.get("prompt")
    model = data.get("model", "mock")
    user_id = current_user.id
    conversation_id = data.get("conversation_id") or str(uuid.uuid4())
    max_tokens = data.get("max_tokens", 1000)
    temperature = data.get("temperature", 0.7)

    # ---------------------------------------------------------
    # 1. CHECK SUBSCRIPTION & LIMITS
    # ---------------------------------------------------------
    subscription = await user_service.get_subscription(db, user_id)
    if not subscription or subscription.status != "active":
        return stream_error("invalid_subscription", "Inactive subscription")
        
    if model not in subscription.allowed_models:
        return stream_error("model_not_allowed", f"Model {model} not allowed")

    # Throttle
    now = time.time()
    last = user_last_request.get(user_id, 0.0)
    if now - last < 0.5: pass
    user_last_request[user_id] = now

    # ---------------------------------------------------------
    # 2. PREPARE PROVIDER
    # ---------------------------------------------------------
    provider = llm_factory.create_provider(model)
    try:
        estimated = provider.count_tokens(prompt)
    except Exception:
        estimated = len(prompt.split())

    # Check credits conservatively
    needed = int((estimated + max_tokens) * models.MODEL_CREDIT_COSTS.get(model, 0.01))
    
    if subscription.credits_remaining < needed:
        return stream_error("insufficient_credits", f"Need ~{needed} credits")

    # ---------------------------------------------------------
    # 3. STREAM & SAVE
    # ---------------------------------------------------------
    async def event_stream():
        full_response = ""
        any_chunk_sent = False

        try:
            async for chunk in provider.stream_generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature):
                chunk_text = chunk if isinstance(chunk, str) else str(chunk)
                if not chunk_text or not chunk_text.strip(): 
                    continue

                payload = json.dumps({"type": "chunk", "content": chunk_text})
                yield f"data: {payload}\n\n"
                full_response += chunk_text
                any_chunk_sent = True

        except Exception as e:
            # Error handling logic
            msg = str(e).lower()
            if "quota" in msg or "limit" in msg:
                payload = json.dumps({"type": "error", "error": "provider_error", "message": str(e)})
                yield f"data: {payload}\n\n"
                return

            # Fallback to non-streaming
            try:
                if not any_chunk_sent:
                    result = await provider.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                    content = result.get('content', '')
                    if content:
                        async for part in emulate_stream_text(content):
                            payload = json.dumps({"type": "chunk", "content": part})
                            yield f"data: {payload}\n\n"
                            full_response += part
                            any_chunk_sent = True
                        full_response = content
            except Exception as e2:
                 payload = json.dumps({"type": "error", "error": "llm_error", "message": str(e2)})
                 yield f"data: {payload}\n\n"
                 return

        # FINALIZE
        try:
            prompt_tokens = estimated
            completion_tokens = provider.count_tokens(full_response) if hasattr(provider, 'count_tokens') else len(full_response.split())
            total_tokens = prompt_tokens + completion_tokens
            cost = 0.0
            if hasattr(provider, 'estimate_cost'):
                cost = provider.estimate_cost(prompt_tokens, completion_tokens, model)

            # DB Update
            multiplier = models.MODEL_CREDIT_COSTS.get(model, 0.01)
            credits_to_deduct = int(total_tokens * multiplier)
            
            updated_sub = await user_service.deduct_credits_atomic(db, user_id, credits_to_deduct)
            
            # Ensure conversation exists
            await chat_service.ensure_conversation(db, conversation_id, user_id, title=prompt[:100] if prompt else None)
            
            # Check if user message already exists (to avoid duplicates when multiple models respond)
            from app.db_models import Message, MessageRole
            from sqlalchemy import select, and_
            from datetime import datetime, timedelta
            
            # Check if a user message with this content was saved in the last 10 seconds
            recent_cutoff = datetime.now() - timedelta(seconds=10)
            existing_user_msg = await db.execute(
                select(Message).where(
                    and_(
                        Message.conversation_id == conversation_id,
                        Message.role == MessageRole.user,
                        Message.content == prompt,
                        Message.created_at >= recent_cutoff
                    )
                ).order_by(Message.created_at.desc()).limit(1)
            )
            
            # Only save user message if it doesn't already exist
            if existing_user_msg.scalar_one_or_none() is None:
                await chat_service.save_message(
                    db, conversation_id, "user", prompt, None,
                    {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    0.0
                )
            
            # Save assistant message
            await chat_service.save_message(
                db, conversation_id, "assistant", full_response, model,
                {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens},
                cost
            )
            await chat_service.track_usage(db, user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)
            
            final_creds_rem = updated_sub.credits_remaining
            final_creds_used = updated_sub.credits_used

            payload = json.dumps({
                "type": "done", 
                "message_id": str(uuid.uuid4()), 
                "tokens_used": total_tokens, 
                "credits_used": final_creds_used,
                "credits_remaining": final_creds_rem,
                "model": model
            })
            yield f"data: {payload}\n\n"
            
        except Exception as e:
            print(f"Error finalizing stream: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/chat/models/formatted")
async def list_models_formatted():
    """
    Returns rich model data for the pricing page and model selector.
    """
    formatted_models = []
    
    # Iterate over our new central MODEL_META source of truth
    for model_id, meta in models.MODEL_META.items():
        # Determine tier
        tier = "enterprise"
        for t_name, t_data in models.SUBSCRIPTION_TIERS.items():
            if model_id in t_data["allowed_models"]:
                tier = t_name
                break # Assign lowest tier found
        
        formatted_models.append({
            "value": model_id,
            "label": meta["label"],
            "provider": meta["provider"],
            "tier": tier,
            "description": meta.get("description", ""),
            "input_cost": meta.get("input_cost_1k", 0),
            "output_cost": meta.get("output_cost_1k", 0)
        })
        
    return formatted_models


@router.get("/conversations/")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns conversations with calculated costs for the authenticated user"""
    return await chat_service.get_user_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a conversation. Verifies user owns the conversation."""
    from app.db_models import Conversation
    from sqlalchemy import select
    
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return await chat_service.get_conversation_messages(db, conversation_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages. Verifies user owns the conversation."""
    from app.db_models import Conversation
    from sqlalchemy import select
    
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conv)
    await db.commit()
    
    return {"message": "Conversation deleted"}


@router.get("/chat/models")
async def list_models():
    return llm_factory.get_available_models()
