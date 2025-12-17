from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .. import schemas, models
from ..database import get_db
from ..db_models import Subscription, User
from ..services import user_service
from ..routers.auth import get_current_user

router = APIRouter(prefix="", tags=["Subscriptions"])

@router.get("/subscriptions/me", response_model=schemas.SubscriptionDetail)
async def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    sub = await user_service.get_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return schemas.SubscriptionDetail(
        id=sub.id,
        user_id=sub.user_id,
        tier_id=sub.tier_id,
        tier_name=sub.tier_name,
        allowed_models=sub.allowed_models,
        tokens_limit=sub.tokens_limit,
        tokens_used=sub.tokens_used,
        tokens_remaining=sub.tokens_remaining,
        credits_limit=sub.credits_limit,
        credits_used=sub.credits_used,
        credits_remaining=sub.credits_remaining,
        monthly_cost_usd=sub.monthly_cost_usd,
        monthly_api_cost_usd=sub.monthly_api_cost_usd,
        requests_this_minute=0, 
        status=sub.status.value if hasattr(sub.status, 'value') else sub.status,
        created_at=sub.created_at,
        expires_at=sub.expires_at,
    )


@router.post("/subscriptions/me/upgrade", response_model=schemas.SubscriptionDetail)
async def upgrade_subscription(
    tier: str = "pro",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if tier not in models.SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    sub = await user_service.get_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    tier_info = models.SUBSCRIPTION_TIERS[tier]
    
    # Update DB object
    sub.tier_id = tier_info["tier_id"]
    sub.tier_name = tier_info["name"]
    sub.plan_type = tier
    sub.allowed_models = tier_info["allowed_models"]
    sub.tokens_limit = tier_info["tokens_per_month"]
    sub.tokens_remaining = sub.tokens_limit - sub.tokens_used # Reset logic can vary
    sub.credits_limit = tier_info.get("credits_per_month", tier_info["tokens_per_month"])
    sub.credits_remaining = sub.credits_limit - sub.credits_used
    sub.rate_limit_per_minute = tier_info["rate_limit_per_minute"]
    sub.monthly_cost_usd = tier_info["cost_usd"]

    await db.commit()
    await db.refresh(sub)

    return schemas.SubscriptionDetail(
        id=sub.id,
        user_id=sub.user_id,
        tier_id=sub.tier_id,
        tier_name=sub.tier_name,
        allowed_models=sub.allowed_models,
        tokens_limit=sub.tokens_limit,
        tokens_used=sub.tokens_used,
        tokens_remaining=sub.tokens_remaining,
        credits_limit=sub.credits_limit,
        credits_used=sub.credits_used,
        credits_remaining=sub.credits_remaining,
        monthly_cost_usd=sub.monthly_cost_usd,
        monthly_api_cost_usd=sub.monthly_api_cost_usd,
        requests_this_minute=0,
        status=sub.status.value if hasattr(sub.status, 'value') else sub.status,
        created_at=sub.created_at,
        expires_at=sub.expires_at,
    )

@router.post("/subscriptions/me/add-tokens")
async def add_tokens(
    tokens: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if tokens <= 0:
        raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    sub = await user_service.get_subscription(db, current_user.id)
    if not sub: raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub.tokens_remaining += tokens
    sub.tokens_limit += tokens
    await db.commit()
    
    return {
        "message": f"Added {tokens} tokens",
        "tokens_remaining": sub.tokens_remaining,
        "tokens_limit": sub.tokens_limit
    }

@router.post("/subscriptions/me/add-credits")
async def add_credits(
    credits: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    sub = await user_service.get_subscription(db, current_user.id)
    if not sub: raise HTTPException(status_code=404, detail="Subscription not found")
    
    sub.credits_remaining += credits
    sub.credits_limit += credits
    await db.commit()
    
    return {
        "message": f"Added {credits} credits",
        "credits_remaining": sub.credits_remaining,
        "credits_limit": sub.credits_limit
    }

@router.put("/subscriptions/me/use-tokens", response_model=schemas.TokenUsageResponse)
async def use_tokens(
    tokens: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # This endpoint is mostly for testing manual deductions
    if tokens <= 0: raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    sub = await user_service.get_subscription(db, current_user.id)
    if not sub: raise HTTPException(status_code=404, detail="Subscription not found")
    
    if sub.tokens_remaining < tokens:
        raise HTTPException(status_code=402, detail="Insufficient tokens")
    
    sub.tokens_used += tokens
    sub.tokens_remaining -= tokens
    await db.commit()
    
    percentage = (sub.tokens_used / sub.tokens_limit) * 100
    return schemas.TokenUsageResponse(
        tokens_used=sub.tokens_used,
        tokens_remaining=sub.tokens_remaining,
        tokens_limit=sub.tokens_limit,
        percentage_used=round(percentage, 2)
    )

@router.put("/subscriptions/me/use-credits", response_model=schemas.TokenUsageResponse)
async def use_credits(
    credits: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if credits <= 0: raise HTTPException(status_code=400, detail="Credits must be positive")
    
    sub = await user_service.deduct_credits_atomic(db, current_user.id, credits)
    # Re-use schema
    percentage = 0
    if sub.credits_limit > 0:
        percentage = (sub.credits_used / sub.credits_limit) * 100
        
    return schemas.TokenUsageResponse(
        tokens_used=sub.credits_used, # Mapping credits to the same schema slots for simplicity
        tokens_remaining=sub.credits_remaining,
        tokens_limit=sub.credits_limit,
        percentage_used=round(percentage, 2)
    )

@router.get("/subscriptions/")
async def list_available_tiers():
    return {
        tier_name: {
            "tier_id": tier["tier_id"],
            "name": tier["name"],
            "allowed_models": tier["allowed_models"],
            "tokens_per_month": tier["tokens_per_month"],
            "rate_limit_per_minute": tier["rate_limit_per_minute"],
            "cost_usd": tier["cost_usd"],
        }
        for tier_name, tier in models.SUBSCRIPTION_TIERS.items()
    }