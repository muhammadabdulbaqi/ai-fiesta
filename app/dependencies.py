from fastapi import HTTPException
from typing import Dict
from datetime import datetime, timedelta
from collections import defaultdict

from . import models


def get_user_or_404(user_id: str) -> Dict:
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return models.users_db[user_id]


def get_subscription_or_404_by_user(user_id: str) -> Dict:
    for sub in models.subscriptions_db.values():
        if sub["user_id"] == user_id:
            return sub
    raise HTTPException(status_code=404, detail="Subscription not found")


def check_subscription_active(subscription: Dict) -> None:
    """Verify subscription is active and not expired"""
    if subscription["status"] != "active":
        raise HTTPException(status_code=403, detail=f"Subscription is {subscription['status']}")
    if subscription.get("expires_at") and datetime.now() > subscription["expires_at"]:
        raise HTTPException(status_code=403, detail="Subscription expired")


def check_model_access(subscription: Dict, model: str) -> None:
    """Verify user has access to the requested model"""
    if model not in subscription.get("allowed_models", []):
        raise HTTPException(
            status_code=403,
            detail=f"Model {model} not available in {subscription['tier_name']} tier. Available: {subscription['allowed_models']}"
        )


def check_tokens_available(subscription: Dict, estimated_tokens: int) -> None:
    """Verify user has enough tokens"""
    if subscription["tokens_remaining"] < estimated_tokens:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient tokens. Required: {estimated_tokens}, Available: {subscription['tokens_remaining']}"
        )


def deduct_tokens(subscription: Dict, tokens_used: int) -> None:
    """Deduct tokens from user's subscription"""
    subscription["tokens_used"] += tokens_used
    subscription["tokens_remaining"] -= tokens_used


def track_api_cost(user_id: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
    """Track API costs for billing and analytics"""
    cost_id = str(__import__('uuid').uuid4())
    models.cost_tracker_db[cost_id] = {
        "id": cost_id,
        "user_id": user_id,
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": cost_usd,
        "created_at": datetime.now(),
    }
    
    # Also accumulate in subscription's monthly cost
    subscription = get_subscription_or_404_by_user(user_id)
    subscription["monthly_api_cost_usd"] += cost_usd


def track_real_api_usage(user_id: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
    """Track real API usage (actual calls to external APIs)"""
    if user_id not in models.api_usage_db:
        models.api_usage_db[user_id] = {}
    
    if provider not in models.api_usage_db[user_id]:
        models.api_usage_db[user_id][provider] = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "models_used": set(),
            "last_used": None,
        }
    
    usage = models.api_usage_db[user_id][provider]
    usage["calls"] += 1
    usage["prompt_tokens"] += prompt_tokens
    usage["completion_tokens"] += completion_tokens
    usage["total_tokens"] += prompt_tokens + completion_tokens
    usage["cost_usd"] += cost_usd
    usage["last_used"] = datetime.now()
    if model not in usage["models_used"]:
        usage["models_used"].add(model)


def get_user_cost_summary(user_id: str) -> Dict:
    """Get total API costs for a user"""
    user_costs = [c for c in models.cost_tracker_db.values() if c["user_id"] == user_id]
    total_tokens = sum(c["total_tokens"] for c in user_costs)
    total_cost = sum(c["cost_usd"] for c in user_costs)
    return {
        "user_id": user_id,
        "total_api_calls": len(user_costs),
        "total_tokens_consumed": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "breakdown_by_provider": _breakdown_by_provider(user_costs),
    }


def _breakdown_by_provider(costs: list) -> Dict:
    breakdown = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
    for cost in costs:
        provider = cost["provider"]
        breakdown[provider]["calls"] += 1
        breakdown[provider]["tokens"] += cost["total_tokens"]
        breakdown[provider]["cost"] += cost["cost_usd"]
    return {k: {**v, "cost": round(v["cost"], 4)} for k, v in breakdown.items()}


def get_real_api_usage_summary(user_id: str) -> Dict:
    """Get real API usage summary for a user"""
    if user_id not in models.api_usage_db:
        return {
            "user_id": user_id,
            "total_api_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "by_provider": {},
        }
    
    user_usage = models.api_usage_db[user_id]
    total_calls = sum(p["calls"] for p in user_usage.values())
    total_tokens = sum(p["total_tokens"] for p in user_usage.values())
    total_cost = sum(p["cost_usd"] for p in user_usage.values())
    
    by_provider = {}
    for provider, data in user_usage.items():
        by_provider[provider] = {
            "calls": data["calls"],
            "prompt_tokens": data["prompt_tokens"],
            "completion_tokens": data["completion_tokens"],
            "total_tokens": data["total_tokens"],
            "cost_usd": round(data["cost_usd"], 4),
            "models_used": list(data["models_used"]),
            "last_used": data["last_used"].isoformat() if data["last_used"] else None,
        }
    
    return {
        "user_id": user_id,
        "total_api_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "by_provider": by_provider,
    }


# Request rate limiting (in-memory for now)
rate_limiter = defaultdict(list)  # {user_id: [timestamps]}


def check_rate_limit(user_id: str, rate_limit_per_minute: int) -> None:
    """Check if user exceeds rate limit"""
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old entries
    rate_limiter[user_id] = [ts for ts in rate_limiter[user_id] if ts > minute_ago]
    
    if len(rate_limiter[user_id]) >= rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {rate_limit_per_minute} requests per minute"
        )
    
    # Add current request
    rate_limiter[user_id].append(now)


# Conversation/message stores for later phases
conversations_db = {}
messages_db = {}

