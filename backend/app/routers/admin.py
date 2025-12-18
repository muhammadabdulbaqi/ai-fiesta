from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func, delete
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
    # Use LEFT JOIN from User to Subscription to show all users, even without subscriptions
    result = await db.execute(
        select(User, Subscription)
        .outerjoin(Subscription, User.id == Subscription.user_id)
        .order_by(User.created_at.desc())
    )
    rows = result.all()
    
    subscriptions_list = []
    for user, sub in rows:
        if sub:  # User has a subscription
            subscriptions_list.append({
                "user_id": user.id,
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
            })
        else:  # User without subscription (shouldn't happen, but handle it)
            subscriptions_list.append({
                "user_id": user.id,
                "user_email": user.email,
                "user_username": user.username,
                "tier": "No Subscription",
                "tier_id": "none",
                "tokens_limit": 0,
                "tokens_used": 0,
                "tokens_remaining": 0,
                "credits_limit": 0,
                "credits_used": 0,
                "credits_remaining": 0,
                "status": "inactive",
                "monthly_cost_usd": 0.0,
                "monthly_api_cost_usd": 0.0,
            })
    
    return subscriptions_list


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


@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Make a regular user an admin by upgrading their subscription to admin tier"""
    from .. import models
    from datetime import datetime
    
    # Get user's subscription
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="User subscription not found")
    
    # Get admin tier config
    admin_tier = models.SUBSCRIPTION_TIERS.get("admin")
    if not admin_tier:
        raise HTTPException(status_code=500, detail="Admin tier not configured")
    
    # Update subscription to admin tier
    subscription.tier_id = "admin"
    subscription.tier_name = "Admin"
    subscription.allowed_models = admin_tier["allowed_models"]
    subscription.tokens_limit = admin_tier["tokens_per_month"]
    subscription.tokens_remaining = admin_tier["tokens_per_month"] - subscription.tokens_used
    subscription.credits_limit = admin_tier["credits_per_month"]
    subscription.credits_remaining = admin_tier["credits_per_month"] - subscription.credits_used
    subscription.monthly_cost_usd = admin_tier["cost_usd"]
    subscription.rate_limit_per_minute = admin_tier["rate_limit_per_minute"]
    
    # Also create admin user record if it doesn't exist
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if user:
        admin_result = await db.execute(
            select(AdminUser).where(AdminUser.email == user.email)
        )
        existing_admin = admin_result.scalar_one_or_none()
        
        if not existing_admin:
            # Create admin user with same credentials
            from ..services import admin_service
            try:
                admin = await admin_service.create_admin(
                    db, 
                    user.email, 
                    user.username, 
                    user.hashed_password
                )
            except Exception as e:
                # If admin already exists (race condition), that's fine
                if "already exists" not in str(e).lower():
                    raise
    
    await db.commit()
    return {"message": "User upgraded to admin", "user_id": user_id}


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a regular user (admin only)"""
    # Prevent deleting yourself
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is an admin (prevent deleting admins)
    admin_result = await db.execute(
        select(AdminUser).where(AdminUser.email == user.email)
    )
    admin = admin_result.scalar_one_or_none()
    
    if admin:
        raise HTTPException(status_code=400, detail="Cannot delete admin users")
    
    # Delete subscription first (to avoid foreign key constraint violation)
    subscription_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = subscription_result.scalar_one_or_none()
    if subscription:
        await db.execute(delete(Subscription).where(Subscription.id == subscription.id))
    
    # Delete user (cascade will handle conversations, messages)
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/add-tokens")
async def admin_add_tokens(
    user_id: str,
    tokens: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to add tokens to any user's subscription"""
    if tokens <= 0:
        raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub.tokens_remaining += tokens
    sub.tokens_limit += tokens
    await db.commit()
    await db.refresh(sub)
    
    return {
        "message": f"Added {tokens} tokens",
        "tokens_remaining": sub.tokens_remaining,
        "tokens_limit": sub.tokens_limit,
        "tokens_used": sub.tokens_used
    }


@router.post("/users/{user_id}/add-credits")
async def admin_add_credits(
    user_id: str,
    credits: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to add credits to any user's subscription"""
    if credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")
    
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub.credits_remaining += credits
    sub.credits_limit += credits
    await db.commit()
    await db.refresh(sub)
    
    return {
        "message": f"Added {credits} credits",
        "credits_remaining": sub.credits_remaining,
        "credits_limit": sub.credits_limit,
        "credits_used": sub.credits_used
    }


@router.post("/users/{user_id}/upgrade")
async def admin_upgrade_subscription(
    user_id: str,
    tier: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to upgrade any user's subscription tier"""
    from .. import models
    
    if tier not in models.SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")
    
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    tier_info = models.SUBSCRIPTION_TIERS[tier]
    
    # Update subscription
    sub.tier_id = tier_info["tier_id"]
    sub.tier_name = tier_info["name"]
    sub.plan_type = tier
    sub.allowed_models = tier_info["allowed_models"]
    sub.tokens_limit = tier_info["tokens_per_month"]
    sub.tokens_remaining = tier_info["tokens_per_month"] - sub.tokens_used
    sub.credits_limit = tier_info.get("credits_per_month", tier_info["tokens_per_month"])
    sub.credits_remaining = sub.credits_limit - sub.credits_used
    sub.rate_limit_per_minute = tier_info["rate_limit_per_minute"]
    sub.monthly_cost_usd = tier_info["cost_usd"]
    
    await db.commit()
    await db.refresh(sub)
    
    return {
        "message": f"Subscription upgraded to {tier}",
        "tier_id": sub.tier_id,
        "tier_name": sub.tier_name
    }
