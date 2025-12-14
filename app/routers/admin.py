from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models
from ..database import get_db
from ..db_models import User, Subscription, APIUsage, CostTracker
from ..config import settings
from ..dependencies import get_user_cost_summary, get_user_or_404, get_subscription_or_404_by_user, get_real_api_usage_summary

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/costs")
async def get_all_costs(db: AsyncSession = Depends(get_db)):
    """Get cost report for all users"""
    if settings.use_database:
        # DB Implementation
        # Aggregate CostTracker by provider
        result = await db.execute(
            select(
                CostTracker.provider,
                func.count(CostTracker.id),
                func.sum(CostTracker.total_tokens),
                func.sum(CostTracker.cost_usd)
            ).group_by(CostTracker.provider)
        )
        rows = result.all()
        
        total_by_provider = {}
        for provider, calls, tokens, cost in rows:
            total_by_provider[provider] = {
                "calls": calls,
                "tokens": tokens,
                "cost": cost
            }
        
        # Get users list for response (lite version)
        u_res = await db.execute(select(User))
        users = u_res.scalars().all()
        user_summaries = [{"user_id": u.id, "username": u.username} for u in users]
        
        return {
            "total_users": len(users),
            "total_by_provider": total_by_provider,
            "users": user_summaries
        }
    else:
        # Legacy
        total_by_provider = {}
        user_summaries = []
        for user_id in models.users_db.keys():
            try:
                cost_summary = get_user_cost_summary(user_id)
                user_summaries.append({"user_id": user_id, **cost_summary})
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
async def list_all_subscriptions(db: AsyncSession = Depends(get_db)):
    """List all user subscriptions"""
    if settings.use_database:
        result = await db.execute(select(Subscription))
        subs = result.scalars().all()
        return [{
            "user_id": sub.user_id,
            "tier": sub.tier_name,
            "tokens_limit": sub.tokens_limit,
            "tokens_used": sub.tokens_used,
            "tokens_remaining": sub.tokens_remaining,
            "credits_limit": sub.credits_limit,
            "credits_used": sub.credits_used,
            "credits_remaining": sub.credits_remaining,
            "status": sub.status.value if hasattr(sub.status, 'value') else sub.status,
            "monthly_cost_usd": sub.monthly_cost_usd,
            "monthly_api_cost_usd": sub.monthly_api_cost_usd,
        } for sub in subs]
    else:
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


@router.get("/usage")
async def get_all_real_api_usage(db: AsyncSession = Depends(get_db)):
    """Get real API usage stats for dashboard"""
    if settings.use_database:
        # Sums from APIUsage table
        result = await db.execute(
            select(
                func.sum(APIUsage.calls),
                func.sum(APIUsage.total_tokens),
                func.sum(APIUsage.cost_usd)
            )
        )
        total_calls, total_tokens, total_cost = result.first()
        
        # Breakdown by provider
        prov_res = await db.execute(
            select(
                APIUsage.provider,
                func.sum(APIUsage.calls),
                func.sum(APIUsage.total_tokens),
                func.sum(APIUsage.cost_usd)
            ).group_by(APIUsage.provider)
        )
        by_provider = {}
        for p, c, t, cost in prov_res.all():
            by_provider[p] = {
                "calls": c,
                "tokens": t,
                "cost": round(cost, 4) if cost else 0
            }

        # Count users with usage
        u_count_res = await db.execute(select(func.count(APIUsage.user_id.distinct())))
        users_with_usage = u_count_res.scalar()

        return {
            "total_users_with_usage": users_with_usage or 0,
            "total_api_calls_made": total_calls or 0,
            "total_tokens_consumed": total_tokens or 0,
            "total_cost_usd": round(total_cost, 4) if total_cost else 0,
            "by_provider": by_provider,
            "users": [] # Detailed list omitted for overview
        }
    else:
        # Legacy
        total_by_provider = {}
        user_summaries = []
        
        for user_id in models.users_db.keys():
            try:
                usage = get_real_api_usage_summary(user_id)
                user_summaries.append({"user_id": user_id, **usage})
                for provider, provider_data in usage.get("by_provider", {}).items():
                    if provider not in total_by_provider:
                        total_by_provider[provider] = {"calls": 0, "tokens": 0, "cost": 0.0}
                    total_by_provider[provider]["calls"] += provider_data["calls"]
                    total_by_provider[provider]["tokens"] += provider_data["total_tokens"]
                    total_by_provider[provider]["cost"] += provider_data["cost_usd"]
            except Exception: pass
        
        return {
            "total_users_with_usage": len(user_summaries),
            "total_api_calls_made": sum(u["total_api_calls"] for u in user_summaries),
            "total_tokens_consumed": sum(u["total_tokens"] for u in user_summaries),
            "total_cost_usd": round(sum(u["total_cost_usd"] for u in user_summaries), 4),
            "by_provider": {k: {**v, "cost": round(v["cost"], 4)} for k, v in total_by_provider.items()},
            "users": user_summaries,
        }