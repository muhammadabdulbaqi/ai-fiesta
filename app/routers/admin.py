from fastapi import APIRouter, HTTPException
from .. import models
from ..dependencies import get_user_cost_summary, get_user_or_404, get_subscription_or_404_by_user, get_real_api_usage_summary

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/costs/{user_id}")
async def get_user_cost_report(user_id: str):
    """Get API cost report for a specific user"""
    user = get_user_or_404(user_id)
    cost_summary = get_user_cost_summary(user_id)
    
    subscription = get_subscription_or_404_by_user(user_id)
    
    return {
        "user": {"id": user["id"], "email": user["email"], "usernamae": user["username"]},
        "subscription": {
            "tier": subscription["tier_name"],
            "monthly_cost_usd": subscription["monthly_cost_usd"],
            "monthly_api_cost_usd": subscription["monthly_api_cost_usd"],
        },
        "usage": cost_summary,
    }


@router.get("/costs")
async def get_all_costs():
    """Get cost report for all users (admin only)"""
    total_by_provider = {}
    user_summaries = []
    
    for user_id in models.users_db.keys():
        try:
            cost_summary = get_user_cost_summary(user_id)
            user_summaries.append({
                "user_id": user_id,
                **cost_summary
            })
            
            for provider, breakdown in cost_summary["breakdown_by_provider"].items():
                if provider not in total_by_provider:
                    total_by_provider[provider] = {"calls": 0, "tokens": 0, "cost": 0.0}
                total_by_provider[provider]["calls"] += breakdown["calls"]
                total_by_provider[provider]["tokens"] += breakdown["tokens"]
                total_by_provider[provider]["cost"] += breakdown["cost"]
        except Exception:
            pass
    
    return {
        "total_users": len(models.users_db),
        "total_by_provider": total_by_provider,
        "users": user_summaries,
    }


@router.get("/subscriptions")
async def list_all_subscriptions():
    """List all user subscriptions (admin only)"""
    subs = []
    for sub in models.subscriptions_db.values():
        subs.append({
            "user_id": sub["user_id"],
            "tier": sub["tier_name"],
            "tokens_limit": sub["tokens_limit"],
            "tokens_used": sub["tokens_used"],
            "tokens_remaining": sub["tokens_remaining"],
            "credits_limit": sub.get("credits_limit"),
            "credits_used": sub.get("credits_used"),
            "credits_remaining": sub.get("credits_remaining"),
            "status": sub["status"],
            "monthly_cost_usd": sub["monthly_cost_usd"],
            "monthly_api_cost_usd": sub["monthly_api_cost_usd"],
        })
    return subs


@router.get("/tier-breakdown")
async def get_tier_breakdown():
    """See how many users per tier"""
    breakdown = {}
    for sub in models.subscriptions_db.values():
        tier = sub["tier_name"]
        if tier not in breakdown:
            breakdown[tier] = {"count": 0, "users": []}
        breakdown[tier]["count"] += 1
        breakdown[tier]["users"].append(sub["user_id"])
    return breakdown


@router.get("/usage/{user_id}")
async def get_user_real_api_usage(user_id: str):
    """Get real API usage for a specific user (actual API calls made)"""
    user = get_user_or_404(user_id)
    usage = get_real_api_usage_summary(user_id)
    
    return {
        "user": {"id": user["id"], "email": user["email"], "username": user["username"]},
        "real_api_usage": usage,
    }


@router.get("/usage")
async def get_all_real_api_usage():
    """Get real API usage across all users and providers"""
    total_by_provider = {
        "gemini": {"calls": 0, "tokens": 0, "cost": 0.0},
        "openai": {"calls": 0, "tokens": 0, "cost": 0.0},
        "anthropic": {"calls": 0, "tokens": 0, "cost": 0.0},
    }
    
    user_summaries = []
    
    for user_id in models.users_db.keys():
        try:
            usage = get_real_api_usage_summary(user_id)
            user_summaries.append({
                "user_id": user_id,
                **usage
            })
            
            # Aggregate by provider
            for provider, provider_data in usage.get("by_provider", {}).items():
                if provider in total_by_provider:
                    total_by_provider[provider]["calls"] += provider_data["calls"]
                    total_by_provider[provider]["tokens"] += provider_data["total_tokens"]
                    total_by_provider[provider]["cost"] += provider_data["cost_usd"]
        except Exception:
            pass
    
    return {
        "total_users_with_usage": len(user_summaries),
        "total_api_calls_made": sum(u["total_api_calls"] for u in user_summaries),
        "total_tokens_consumed": sum(u["total_tokens"] for u in user_summaries),
        "total_cost_usd": round(sum(u["total_cost_usd"] for u in user_summaries), 4),
        "by_provider": {k: {**v, "cost": round(v["cost"], 4)} for k, v in total_by_provider.items()},
        "users": user_summaries,
    }


@router.get("/usage/provider/{provider}")
async def get_provider_usage(provider: str):
    """Get usage statistics for a specific provider (gemini, openai, anthropic)"""
    provider_lower = provider.lower()
    total_calls = 0
    total_tokens = 0
    total_cost = 0.0
    user_data = []
    
    for user_id, user_usage_dict in models.api_usage_db.items():
        if provider_lower in user_usage_dict:
            data = user_usage_dict[provider_lower]
            total_calls += data["calls"]
            total_tokens += data["total_tokens"]
            total_cost += data["cost_usd"]
            user_data.append({
                "user_id": user_id,
                "calls": data["calls"],
                "tokens": data["total_tokens"],
                "cost_usd": round(data["cost_usd"], 4),
                "models_used": list(data["models_used"]),
                "last_used": data["last_used"].isoformat() if data["last_used"] else None,
            })
    
    return {
        "provider": provider_lower,
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "users_count": len(user_data),
        "users": user_data,
    }
