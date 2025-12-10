from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
import os
from datetime import datetime
import uuid
from collections import defaultdict
import time

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
    check_credits_available,
    deduct_credits,
    track_api_cost,
    track_real_api_usage,
    check_rate_limit,
)
from ..utils.stream_emulation import emulate_stream_text

router = APIRouter(prefix="", tags=["Chat"])

# Simple per-user spacing tracker to avoid provider free-tier rate limits (seconds)
user_last_request = defaultdict(float)


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
    
    # Estimate tokens and check credits
    estimated = provider.count_tokens(request.prompt)
    # Use credits-based check (conservative: include requested max_tokens)
    check_credits_available(subscription, estimated + (request.max_tokens or 1000), model)
    
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

        # Deduct credits based on model multiplier
        credits_deducted = deduct_credits(subscription, total_tokens, model_used)
        
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
            # New credit fields for client-side visibility
            **{"credits_used": subscription.get("credits_used"), "credits_remaining": subscription.get("credits_remaining")}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/models/formatted")
async def list_models_formatted():
    """
    Returns models in a flat format that the frontend expects.
    Each model includes: value, label, provider, tier
    
    Example response:
    [
        {
            "value": "gpt-4",
            "label": "GPT-4",
            "provider": "openai",
            "tier": "enterprise"
        },
        ...
    ]
    """
    from .. import models as app_models
    
    # Get raw models from factory
    raw_models = llm_factory.get_available_models()
    
    # Model tier mapping (which tier can access which models)
    model_tier_map = {}
    for tier_name, tier_info in app_models.SUBSCRIPTION_TIERS.items():
        for model in tier_info["allowed_models"]:
            if model not in model_tier_map:
                model_tier_map[model] = tier_name
    
    # Flatten the nested provider structure
    formatted_models = []
    
    for provider, model_list in raw_models.items():
        for model_id in model_list:
            # Determine tier (default to "pro" if not found)
            tier = model_tier_map.get(model_id, "pro")
            
            # Create a human-readable label
            label = model_id.replace("-", " ").title()
            
            # Special case formatting for common models
            if "gpt" in model_id.lower():
                label = model_id.upper().replace("-", " ")
            elif "claude" in model_id.lower():
                label = "Claude " + model_id.split("-")[1].capitalize()
            elif "gemini" in model_id.lower():
                parts = model_id.split("-")
                if len(parts) >= 2:
                    label = f"Gemini {parts[1].capitalize()}"
                    if len(parts) >= 3:
                        label += f" {parts[2].capitalize()}"
            
            formatted_models.append({
                "value": model_id,
                "label": label,
                "provider": provider,
                "tier": tier
            })
    
    return formatted_models


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


@router.post("/stream/chat")
async def stream_chat(request: Request):
    """HTTP SSE streaming endpoint.

    The client POSTs a JSON body with the same fields as the websocket protocol:
      {"prompt":"...","model":"...","conversation_id":"...","user_id":"...","max_tokens":N}

    The server responds with `text/event-stream` SSE events where each event's `data` is a JSON payload:
      data: {"type":"chunk","content":"..."}
      data: {"type":"done","message_id":"...","tokens_used":N,...}
      data: {"type":"error","error":"code","message":"..."}
    """
    try:
        data = await request.json()
    except Exception:
        return StreamingResponse(("""data: {"type":"error","error":"invalid_request","message":"Expected JSON body"}\n\n"""), media_type="text/event-stream")

    # Validate input
    if not isinstance(data, dict):
        return StreamingResponse(("""data: {"type":"error","error":"invalid_request","message":"Expected JSON object"}\n\n"""), media_type="text/event-stream")

    prompt = data.get("prompt")
    model = data.get("model", "mock")
    user_id = data.get("user_id")
    conversation_id = data.get("conversation_id")
    max_tokens = data.get("max_tokens", 1000)
    temperature = data.get("temperature", 0.7)

    if not user_id:
        return StreamingResponse(("""data: {"type":"error","error":"missing_user","message":"user_id is required"}\n\n"""), media_type="text/event-stream")

    # Validate user and subscription
    try:
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        check_subscription_active(subscription)
    except HTTPException as e:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"invalid_user_or_subscription\", \"message\": \"{str(e.detail)}\"}}\n\n"), media_type="text/event-stream")

    # Check model access
    try:
        check_model_access(subscription, model)
    except HTTPException as e:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"model_not_allowed\", \"message\": \"{str(e.detail)}\"}}\n\n"), media_type="text/event-stream")

    # Per-user spacing
    try:
        now = time.time()
        last = user_last_request.get(user_id, 0.0)
        min_spacing = 4.0
        if now - last < min_spacing:
            wait = int(min_spacing - (now - last))
            return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"rate_limit\", \"message\": \"Please wait {wait} seconds between requests (provider rate limit)\"}}\n\n"), media_type="text/event-stream")
        user_last_request[user_id] = now
    except Exception:
        pass

    # Rate limit check
    try:
        check_rate_limit(user_id, subscription["rate_limit_per_minute"])
    except HTTPException as e:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"rate_limited\", \"message\": \"{str(e.detail)}\"}}\n\n"), media_type="text/event-stream")

    provider = llm_factory.create_provider(model)

    # Estimate tokens conservatively
    try:
        estimated = provider.count_tokens(prompt)
    except Exception:
        estimated = len(prompt.split())

    # Check credits instead of raw tokens
    try:
        check_credits_available(subscription, estimated + max_tokens, model)
    except Exception:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"insufficient_credits\", \"message\": \"Need ~{int((estimated + max_tokens) * 1)} credits (est), but only {subscription.get('credits_remaining')} remaining\"}}\n\n"), media_type="text/event-stream")

    import json

    async def event_stream():
        full_response = ""
        any_chunk_sent = False

        try:
            async for chunk in provider.stream_generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature):
                chunk_text = chunk if isinstance(chunk, str) else str(chunk)
                # Skip empty/whitespace-only chunks to avoid noisy empty SSE events
                if not chunk_text or chunk_text.strip() == "":
                    continue

                # SSE event: data: <json>\n\n
                payload = json.dumps({"type": "chunk", "content": chunk_text})
                yield f"data: {payload}\n\n"
                full_response += chunk_text
                any_chunk_sent = True

        except Exception as e:
            # If this looks like a quota or rate-limit error, surface a clearer message and stop
            try:
                msg = str(e)
                lower = msg.lower()
            except Exception:
                lower = ""

            if "quota" in lower or "limit" in lower or "rate" in lower or "exhausted" in lower:
                try:
                    payload = json.dumps({"type": "error", "error": "llm_error", "message": msg})
                    yield f"data: {payload}\n\n"
                except Exception:
                    pass
                return

            # For other errors, attempt a non-streaming fallback so clients still get an answer
            try:
                result = await provider.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content') if isinstance(result, dict) else str(result)
                # If we have content, emulate streaming it
                if content:
                    async for part in emulate_stream_text(content):
                        if not part or part.strip() == "":
                            continue
                        payload = json.dumps({"type": "chunk", "content": part})
                        yield f"data: {payload}\n\n"
                        full_response += part
                        any_chunk_sent = True
                else:
                    # no content from generate - fall through to finalization which will send done/error
                    pass
            except Exception:
                # if fallback also fails, send an error and stop
                try:
                    payload = json.dumps({"type": "error", "error": "llm_error", "message": str(e)})
                    yield f"data: {payload}\n\n"
                except Exception:
                    pass
                return

        # If provider produced no chunks (silent stream), try non-streaming generate and emulate
        if not any_chunk_sent:
            try:
                # Attempt to fetch the final content non-streaming and stream it to client
                result = await provider.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content') if isinstance(result, dict) else str(result)
                if content:
                    emulated_sent = False
                    async for part in emulate_stream_text(content):
                        if not part or part.strip() == "":
                            continue
                        payload = json.dumps({"type": "chunk", "content": part})
                        yield f"data: {payload}\n\n"
                        full_response += part
                        any_chunk_sent = True
                        emulated_sent = True

                    # If emulation produced nothing (very short content), send the full content as one chunk
                    if not emulated_sent and content:
                        payload = json.dumps({"type": "chunk", "content": content})
                        yield f"data: {payload}\n\n"
                        full_response += content
                        any_chunk_sent = True
                else:
                    # no content from generate - fall through to finalization which will send done/error
                    pass
            except Exception:
                # If this fails, continue to finalization to send done/error
                pass

        # After streaming completes, compute tokens and update subscription
        try:
            prompt_tokens = provider.count_tokens(prompt)
            completion_tokens = provider.count_tokens(full_response)
            total_tokens = prompt_tokens + completion_tokens

            # Deduct credits (based on model multiplier)
            credits = deduct_credits(subscription, total_tokens, model)

            cost = provider.estimate_cost(prompt_tokens, completion_tokens, model) if hasattr(provider, 'estimate_cost') else 0.0
            track_api_cost(user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)
            track_real_api_usage(user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)

            conv_id = conversation_id or str(uuid.uuid4())
            if conv_id not in conversations_db:
                conversations_db[conv_id] = {"id": conv_id, "user_id": user_id, "created_at": datetime.now()}

            message_id = str(uuid.uuid4())
            message = {
                "id": message_id,
                "conversation_id": conv_id,
                "role": "assistant",
                "content": full_response,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "api_cost_usd": round(cost, 6),
                "created_at": datetime.now(),
            }
            messages_db[message_id] = message

            payload = json.dumps({"type": "done", "message_id": message_id, "tokens_used": total_tokens, "tokens_remaining": subscription.get("tokens_remaining"), "model": model, "credits_used": subscription.get("credits_used"), "credits_remaining": subscription.get("credits_remaining")})
            yield f"data: {payload}\n\n"

        except Exception as e:
            try:
                payload = json.dumps({"type": "error", "error": "server_error", "message": str(e)})
                yield f"data: {payload}\n\n"
            except Exception:
                pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")

