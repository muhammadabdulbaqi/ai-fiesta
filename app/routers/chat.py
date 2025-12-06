from fastapi import APIRouter, HTTPException, Header, WebSocket, WebSocketDisconnect
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
    track_api_cost,
    track_real_api_usage,
    check_rate_limit,
)

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


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses.

    Protocol (first message must be JSON):
      {"type": "chat", "prompt": "...", "model": "...", "conversation_id": "...", "user_id": "..."}

    Server streams chunks: {"type": "chunk", "content": "..."}
    On finish: {"type": "done", "message_id": "...", "tokens_used": N, "tokens_remaining": M, "model": "..."}
    On error: {"type": "error", "error": "code", "message": "..."}
    """
    # Feature flag to allow easy revert
    if os.getenv("ENABLE_WS_STREAMING", "true").lower() not in ("1", "true", "yes"):
        await websocket.accept()
        await websocket.send_json({"type": "error", "error": "disabled", "message": "WebSocket streaming is disabled"})
        await websocket.close()
        return

    await websocket.accept()

    try:
        data = await websocket.receive_json()
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": "invalid_message", "message": "Expected initial JSON chat message"})
        except:
            pass
        await websocket.close()
        return

    # Basic validation
    if not isinstance(data, dict) or data.get("type") != "chat":
        await websocket.send_json({"type": "error", "error": "invalid_message_type", "message": "Expected type='chat'"})
        await websocket.close()
        return

    prompt = data.get("prompt")
    model = data.get("model", "mock")
    user_id = data.get("user_id")
    conversation_id = data.get("conversation_id")
    max_tokens = data.get("max_tokens", 1000)
    temperature = data.get("temperature", 0.7)

    if not user_id:
        await websocket.send_json({"type": "error", "error": "missing_user", "message": "user_id is required"})
        await websocket.close()
        return

    # Validate user and subscription
    try:
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        check_subscription_active(subscription)
    except HTTPException as e:
        await websocket.send_json({"type": "error", "error": "invalid_user_or_subscription", "message": str(e.detail)})
        await websocket.close()
        return

    # Check model access
    try:
        check_model_access(subscription, model)
    except HTTPException as e:
        await websocket.send_json({"type": "error", "error": "model_not_allowed", "message": str(e.detail)})
        await websocket.close()
        return

    # Per-user spacing to avoid provider free-tier bursts (e.g., Gemini ~15 req/min)
    try:
        now = time.time()
        last = user_last_request.get(user_id, 0.0)
        min_spacing = 4.0  # seconds between requests per user
        if now - last < min_spacing:
            wait = int(min_spacing - (now - last))
            await websocket.send_json({
                "type": "error",
                "error": "rate_limit",
                "message": f"Please wait {wait} seconds between requests (provider rate limit)"
            })
            await websocket.close()
            return
        user_last_request[user_id] = now
    except Exception:
        # keep going even if rate limit tracking fails
        pass

    # Rate limit check
    try:
        check_rate_limit(user_id, subscription["rate_limit_per_minute"])
    except HTTPException as e:
        await websocket.send_json({"type": "error", "error": "rate_limited", "message": str(e.detail)})
        await websocket.close()
        return

    provider = llm_factory.create_provider(model)

    # Estimate tokens conservatively
    try:
        estimated = provider.count_tokens(prompt)
    except Exception:
        estimated = len(prompt.split())

    if subscription["tokens_remaining"] < (estimated + max_tokens):
        await websocket.send_json({
            "type": "error",
            "error": "insufficient_tokens",
            "message": f"Need ~{estimated + max_tokens} tokens, but only {subscription['tokens_remaining']} remaining"
        })
        await websocket.close()
        return

    # Stream from provider
    full_response = ""
    any_chunk_sent = False

    try:
        async for chunk in provider.stream_generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature):
            # Some providers may yield bytes or dicts; normalize
            if not isinstance(chunk, str):
                try:
                    chunk_text = str(chunk)
                except Exception:
                    continue
            else:
                chunk_text = chunk

            try:
                await websocket.send_json({"type": "chunk", "content": chunk_text})
            except Exception:
                # Client disconnected
                raise WebSocketDisconnect()

            full_response += chunk_text
            any_chunk_sent = True

    except WebSocketDisconnect:
        # Client closed connection; if we already streamed chunks, charge for produced tokens
        if not any_chunk_sent:
            # nothing sent, nothing to charge
            pass
        # we do not re-raise; just cleanup
        return
    except Exception as e:
        # LLM error mid-stream
        try:
            await websocket.send_json({"type": "error", "error": "llm_error", "message": str(e)})
        except:
            pass
        await websocket.close()
        return

    # After streaming completes, compute tokens and update subscription
    try:
        prompt_tokens = provider.count_tokens(prompt)
        completion_tokens = provider.count_tokens(full_response)
        total_tokens = prompt_tokens + completion_tokens

        # Deduct tokens atomically (in-memory here)
        deduct_tokens(subscription, total_tokens)

        # Compute cost and track
        cost = provider.estimate_cost(prompt_tokens, completion_tokens, model) if hasattr(provider, 'estimate_cost') else 0.0
        track_api_cost(user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)
        track_real_api_usage(user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)

        # Save message
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

        # Send done
        await websocket.send_json({
            "type": "done",
            "message_id": message_id,
            "tokens_used": total_tokens,
            "tokens_remaining": subscription.get("tokens_remaining"),
            "model": model,
        })

    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": "server_error", "message": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

