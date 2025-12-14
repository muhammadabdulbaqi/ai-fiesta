from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
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
from app.services import user_service, chat_service

from .. import models

# Legacy In-Memory Imports
from ..dependencies import (
    conversations_db,
    messages_db,
    get_user_or_404,
    get_subscription_or_404_by_user,
    check_subscription_active,
    check_model_access,
    check_credits_available,
    deduct_credits,
    track_api_cost,
    track_real_api_usage,
    check_rate_limit,
)

router = APIRouter(prefix="", tags=["Chat"])

# Simple per-user spacing tracker (In-memory is fine for rate limiting for now)
user_last_request = defaultdict(float)


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
    user_id: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Chat endpoint with real LLMs and subscription management"""
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user-id header")

    model = request.model or "mock"
    subscription = None
    
    # ---------------------------------------------------------
    # 1. VALIDATION & SETUP
    # ---------------------------------------------------------
    if settings.use_database:
        # DB PATH
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        subscription = await user_service.get_subscription(db, user_id)
        if not subscription or subscription.status != "active":
            raise HTTPException(status_code=403, detail="Subscription inactive")
            
        if model not in subscription.allowed_models:
            raise HTTPException(status_code=403, detail=f"Model {model} not allowed")
    else:
        # LEGACY PATH
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        check_subscription_active(subscription)
        check_model_access(subscription, model)
        check_rate_limit(user_id, subscription["rate_limit_per_minute"])

    # ---------------------------------------------------------
    # 2. GENERATION
    # ---------------------------------------------------------
    provider = llm_factory.create_provider(model)
    estimated = provider.count_tokens(request.prompt)
    
    # Check credits logic (simplified check before generation)
    credits_needed = int((estimated + (request.max_tokens or 1000)) * models.MODEL_CREDIT_COSTS.get(model, 0.01))
    
    if settings.use_database:
        if subscription.credits_remaining < credits_needed:
             raise HTTPException(status_code=402, detail="Insufficient credits")
    else:
        check_credits_available(subscription, estimated + (request.max_tokens or 1000), model)

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

        if settings.use_database:
            # DB Write
            multiplier = models.MODEL_CREDIT_COSTS.get(model_used, 0.01)
            credits_deducted = int(total_tokens * multiplier)
            
            # Atomic deduction
            updated_sub = await user_service.deduct_credits_atomic(db, user_id, credits_deducted)
            
            # Save Data
            await chat_service.ensure_conversation(db, conv_id, user_id)
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
        else:
            # Legacy Write
            credits_deducted = deduct_credits(subscription, total_tokens, model_used)
            track_api_cost(user_id, provider.provider_name, model_used, prompt_tokens, completion_tokens, cost)
            track_real_api_usage(user_id, provider.provider_name, model_used, prompt_tokens, completion_tokens, cost)
            
            if conv_id not in conversations_db:
                conversations_db[conv_id] = {"id": conv_id, "user_id": user_id, "created_at": datetime.now()}
            
            messages_db[message_id] = {
                "id": message_id, "conversation_id": conv_id, "role": "assistant",
                "content": content, "model": model_used, "tokens": total_tokens, "created_at": datetime.now()
            }

            return schemas.ChatResponse(
                message_id=message_id,
                conversation_id=conv_id,
                content=content,
                model=model_used,
                tokens_used=total_tokens,
                tokens_remaining=subscription.get("tokens_remaining"),
                credits_used=subscription.get("credits_used"),
                credits_remaining=subscription.get("credits_remaining")
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream/chat")
async def stream_chat(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """HTTP SSE streaming endpoint."""
    try:
        data = await request.json()
    except Exception:
        return stream_error("invalid_request", "Expected JSON body")

    prompt = data.get("prompt")
    model = data.get("model", "mock")
    user_id = data.get("user_id")
    conversation_id = data.get("conversation_id") or str(uuid.uuid4())
    max_tokens = data.get("max_tokens", 1000)
    temperature = data.get("temperature", 0.7)

    if not user_id:
        return stream_error("missing_user", "user_id is required")

    # ---------------------------------------------------------
    # 1. CHECK SUBSCRIPTION & LIMITS
    # ---------------------------------------------------------
    subscription = None
    
    if settings.use_database:
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            return stream_error("invalid_user", "User not found")
        
        subscription = await user_service.get_subscription(db, user_id)
        if not subscription or subscription.status != "active":
            return stream_error("invalid_subscription", "Inactive subscription")
            
        if model not in subscription.allowed_models:
            return stream_error("model_not_allowed", f"Model {model} not allowed")
    else:
        try:
            get_user_or_404(user_id)
            subscription = get_subscription_or_404_by_user(user_id)
            check_subscription_active(subscription)
            check_model_access(subscription, model)
            check_rate_limit(user_id, subscription["rate_limit_per_minute"])
        except HTTPException as e:
            return stream_error("auth_error", str(e.detail))

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
    
    if settings.use_database:
        if subscription.credits_remaining < needed:
            return stream_error("insufficient_credits", f"Need ~{needed} credits")
    else:
        try:
            check_credits_available(subscription, estimated + max_tokens, model)
        except Exception as e:
            return stream_error("insufficient_credits", str(e))

    # ---------------------------------------------------------
    # 3. STREAM & SAVE
    # ---------------------------------------------------------
    async def event_stream():
        full_response = ""
        any_chunk_sent = False

        try:
            async for chunk in provider.stream_generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature):
                chunk_text = chunk if isinstance(chunk, str) else str(chunk)
                if not chunk_text or not chunk_text.strip(): continue

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
            completion_tokens = len(full_response.split())
            total_tokens = prompt_tokens + completion_tokens
            cost = 0.0
            if hasattr(provider, 'estimate_cost'):
                cost = provider.estimate_cost(prompt_tokens, completion_tokens, model)

            if settings.use_database:
                # DB Update
                multiplier = models.MODEL_CREDIT_COSTS.get(model, 0.01)
                credits_to_deduct = int(total_tokens * multiplier)
                
                updated_sub = await user_service.deduct_credits_atomic(db, user_id, credits_to_deduct)
                
                await chat_service.ensure_conversation(db, conversation_id, user_id)
                await chat_service.save_message(
                    db, conversation_id, "assistant", full_response, model,
                    {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens},
                    cost
                )
                await chat_service.track_usage(db, user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)
                
                final_creds_rem = updated_sub.credits_remaining
                final_creds_used = updated_sub.credits_used
            else:
                # Legacy Update
                deduct_credits(subscription, total_tokens, model)
                track_api_cost(user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)
                final_creds_rem = subscription.get("credits_remaining")
                final_creds_used = subscription.get("credits_used")

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
async def list_conversations(user_id: str = Header(None), db: AsyncSession = Depends(get_db)):
    """Returns conversations with calculated costs"""
    if settings.use_database:
        if not user_id: return []
        return await chat_service.get_user_conversations(db, user_id)
    else:
        # Fallback for in-memory mode
        return list(conversations_db.values())


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    if settings.use_database:
        return await chat_service.get_conversation_messages(db, conversation_id)
    else:
        return [m for m in messages_db.values() if m["conversation_id"] == conversation_id]


@router.get("/chat/models")
async def list_models():
    return llm_factory.get_available_models()