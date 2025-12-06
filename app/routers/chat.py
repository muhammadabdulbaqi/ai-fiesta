from fastapi import APIRouter, HTTPException, Header
from datetime import datetime
import uuid

from .. import schemas, models
from ..llm.factory import llm_factory
from ..dependencies import (
    conversations_db,
    messages_db,
    get_user_or_404,
    get_subscription_or_404_by_user,
    check_subscription_active,
    check_model_access,
    check_tokens_available,
    deduct_tokens,
    track_api_cost,
    track_real_api_usage,
    check_rate_limit,
)

router = APIRouter(prefix="", tags=["Chat"])


@router.post("/chat/", response_model=schemas.ChatResponse)
async def chat(request: schemas.ChatRequest, user_id: str = Header(None)):
    """Chat endpoint with real LLMs and subscription management"""
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user-id header")

    # Check user exists
    user = get_user_or_404(user_id)
    
    # Get subscription and validate
    subscription = get_subscription_or_404_by_user(user_id)
    check_subscription_active(subscription)
    
    model = request.model or "mock"
    
    # Check model access
    check_model_access(subscription, model)
    
    # Check rate limit
    check_rate_limit(user_id, subscription["rate_limit_per_minute"])
    
    # Create provider
    provider = llm_factory.create_provider(model)
    
    # Estimate tokens
    estimated = provider.count_tokens(request.prompt)
    check_tokens_available(subscription, estimated + (request.max_tokens or 1000))
    
    try:
        # Call LLM
        result = await provider.generate(
            prompt=request.prompt,
            model=model,
            max_tokens=request.max_tokens or 1000,
            temperature=request.temperature or 0.7,
        )

        # Extract result data
        content = result.get("content") if isinstance(result, dict) else str(result)
        model_used = result.get("model", model) if isinstance(result, dict) else model
        prompt_tokens = result.get("prompt_tokens", 0) if isinstance(result, dict) else 0
        completion_tokens = result.get("completion_tokens", 0) if isinstance(result, dict) else 0
        total_tokens = result.get("total_tokens", prompt_tokens + completion_tokens) if isinstance(result, dict) else (prompt_tokens + completion_tokens)

        # Deduct tokens
        deduct_tokens(subscription, total_tokens)
        
        # Track API cost (provider calculates cost based on tokens)
        cost = provider.estimate_cost(prompt_tokens, completion_tokens, model_used)
        track_api_cost(user_id, provider.provider_name, model_used, prompt_tokens, completion_tokens, cost)
        
        # Track real API usage
        track_real_api_usage(user_id, provider.provider_name, model_used, prompt_tokens, completion_tokens, cost)
        
        # Save conversation/message
        conv_id = request.conversation_id or str(uuid.uuid4())
        if conv_id not in conversations_db:
            conversations_db[conv_id] = {"id": conv_id, "user_id": user_id, "created_at": datetime.now()}

        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "conversation_id": conv_id,
            "role": "assistant",
            "content": content,
            "model": model_used,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "api_cost_usd": round(cost, 4),
            "created_at": datetime.now(),
        }
        messages_db[message_id] = message

        return schemas.ChatResponse(
            message_id=message_id,
            conversation_id=conv_id,
            content=content,
            model=model_used,
            tokens_used=total_tokens,
            tokens_remaining=subscription.get("tokens_remaining"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/")
async def list_conversations():
    return list(conversations_db.values())


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    msgs = [m for m in messages_db.values() if m["conversation_id"] == conversation_id]
    return msgs


@router.get("/chat/models")
async def list_models():
    return llm_factory.get_available_models()

