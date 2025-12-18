from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..db_models import User, Subscription, APIUsage, CostTracker, AdminUser
from ..routers.admin_auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/costs")
async def get_all_costs(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get cost report for all users"""
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


@router.get("/subscriptions")
async def list_all_subscriptions(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all user subscriptions with user information"""
    # Join Subscription with User to get email and username
    result = await db.execute(
        select(Subscription, User)
        .join(User, Subscription.user_id == User.id)
    )
    rows = result.all()
    
    return [{
        "user_id": sub.user_id,
        "user_email": user.email,
        "user_username": user.username,
        "tier": sub.tier_name,
        "tier_id": sub.tier_id,
        "tokens_limit": sub.tokens_limit,
        "tokens_used": sub.tokens_used,
        "tokens_remaining": sub.tokens_remaining,
        "credits_limit": sub.credits_limit,
        "credits_used": sub.credits_used,
        "credits_remaining": sub.credits_remaining,
        "status": sub.status.value if hasattr(sub.status, 'value') else sub.status,
        "monthly_cost_usd": sub.monthly_cost_usd,
        "monthly_api_cost_usd": sub.monthly_api_cost_usd,
    } for sub, user in rows]


@router.get("/usage")
async def get_all_real_api_usage(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get real API usage stats for dashboard"""
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
