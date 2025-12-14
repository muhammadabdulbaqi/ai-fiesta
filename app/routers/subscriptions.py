from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .. import schemas, models
from ..config import settings
from ..database import get_db
from ..db_models import Subscription
from ..services import user_service
from ..dependencies import get_user_or_404, get_subscription_or_404_by_user

router = APIRouter(prefix="", tags=["Subscriptions"])

@router.get("/subscriptions/{user_id}", response_model=schemas.SubscriptionDetail)
async def get_user_subscription(user_id: str, db: AsyncSession = Depends(get_db)):
    if settings.use_database:
        sub = await user_service.get_subscription(db, user_id)
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
    else:
        # Legacy
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        return schemas.SubscriptionDetail(
            id=subscription["id"],
            user_id=subscription["user_id"],
            tier_id=subscription["tier_id"],
            tier_name=subscription["tier_name"],
            allowed_models=subscription["allowed_models"],
            tokens_limit=subscription["tokens_limit"],
            tokens_used=subscription["tokens_used"],
            tokens_remaining=subscription["tokens_remaining"],
            credits_limit=subscription.get("credits_limit"),
            credits_used=subscription.get("credits_used"),
            credits_remaining=subscription.get("credits_remaining"),
            monthly_cost_usd=subscription["monthly_cost_usd"],
            monthly_api_cost_usd=subscription["monthly_api_cost_usd"],
            requests_this_minute=0,
            status=subscription["status"],
            created_at=subscription["created_at"],
            expires_at=subscription.get("expires_at"),
        )


@router.post("/subscriptions/{user_id}/upgrade", response_model=schemas.SubscriptionDetail)
async def upgrade_subscription(user_id: str, tier: str = "pro", db: AsyncSession = Depends(get_db)):
    if tier not in models.SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")

    if settings.use_database:
        sub = await user_service.get_subscription(db, user_id)
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
    else:
        # Legacy
        user = get_user_or_404(user_id)
        old_sub = get_subscription_or_404_by_user(user_id)
        del models.subscriptions_db[old_sub["id"]]
        new_sub = models.create_default_subscription(user_id, tier)
        
        # Manually map to schema
        return schemas.SubscriptionDetail(
            id=new_sub["id"],
            user_id=new_sub["user_id"],
            tier_id=new_sub["tier_id"],
            tier_name=new_sub["tier_name"],
            allowed_models=new_sub["allowed_models"],
            tokens_limit=new_sub["tokens_limit"],
            tokens_used=new_sub["tokens_used"],
            tokens_remaining=new_sub["tokens_remaining"],
            credits_limit=new_sub.get("credits_limit"),
            credits_used=new_sub.get("credits_used"),
            credits_remaining=new_sub.get("credits_remaining"),
            monthly_cost_usd=new_sub["monthly_cost_usd"],
            monthly_api_cost_usd=new_sub["monthly_api_cost_usd"],
            requests_this_minute=0,
            status=new_sub["status"],
            created_at=new_sub["created_at"],
            expires_at=new_sub.get("expires_at"),
        )

@router.post("/subscriptions/{user_id}/add-tokens")
async def add_tokens(user_id: str, tokens: int, db: AsyncSession = Depends(get_db)):
    if tokens <= 0:
        raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    if settings.use_database:
        sub = await user_service.get_subscription(db, user_id)
        if not sub: raise HTTPException(status_code=404, detail="Subscription not found")
        
        sub.tokens_remaining += tokens
        sub.tokens_limit += tokens
        await db.commit()
        
        return {
            "message": f"Added {tokens} tokens",
            "tokens_remaining": sub.tokens_remaining,
            "tokens_limit": sub.tokens_limit
        }
    else:
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        subscription["tokens_remaining"] += tokens
        subscription["tokens_limit"] += tokens
        return {
            "message": f"Added {tokens} tokens",
            "tokens_remaining": subscription["tokens_remaining"],
            "tokens_limit": subscription["tokens_limit"]
        }

@router.post("/subscriptions/{user_id}/add-credits")
async def add_credits(user_id: str, credits: int, db: AsyncSession = Depends(get_db)):
    if credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    if settings.use_database:
        sub = await user_service.get_subscription(db, user_id)
        if not sub: raise HTTPException(status_code=404, detail="Subscription not found")
        
        sub.credits_remaining += credits
        sub.credits_limit += credits
        await db.commit()
        
        return {
            "message": f"Added {credits} credits",
            "credits_remaining": sub.credits_remaining,
            "credits_limit": sub.credits_limit
        }
    else:
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        subscription["credits_remaining"] = subscription.get("credits_remaining", 0) + credits
        subscription["credits_limit"] = subscription.get("credits_limit", 0) + credits
        return {
            "message": f"Added {credits} credits",
            "credits_remaining": subscription["credits_remaining"],
            "credits_limit": subscription["credits_limit"]
        }

@router.put("/subscriptions/{user_id}/use-tokens", response_model=schemas.TokenUsageResponse)
async def use_tokens(user_id: str, tokens: int, db: AsyncSession = Depends(get_db)):
    # This endpoint is mostly for testing manual deductions
    if tokens <= 0: raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    if settings.use_database:
        sub = await user_service.get_subscription(db, user_id)
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
    else:
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        
        if subscription["tokens_remaining"] < tokens:
            raise HTTPException(status_code=402, detail="Insufficient tokens")
        
        subscription["tokens_used"] += tokens
        subscription["tokens_remaining"] -= tokens
        
        percentage_used = (subscription["tokens_used"] / subscription["tokens_limit"]) * 100
        return schemas.TokenUsageResponse(
            tokens_used=subscription["tokens_used"],
            tokens_remaining=subscription["tokens_remaining"],
            tokens_limit=subscription["tokens_limit"],
            percentage_used=round(percentage_used, 2),
        )

@router.put("/subscriptions/{user_id}/use-credits", response_model=schemas.TokenUsageResponse)
async def use_credits(user_id: str, credits: int, db: AsyncSession = Depends(get_db)):
    if credits <= 0: raise HTTPException(status_code=400, detail="Credits must be positive")
    
    if settings.use_database:
        sub = await user_service.deduct_credits_atomic(db, user_id, credits)
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
    else:
        # Legacy
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)

        if subscription.get("credits_remaining", 0) < credits:
            raise HTTPException(status_code=402, detail="Insufficient credits")

        subscription["credits_used"] = subscription.get("credits_used", 0) + credits
        subscription["credits_remaining"] = subscription.get("credits_remaining", 0) - credits

        percentage_used = 0.0
        if subscription.get("credits_limit"):
            percentage_used = (subscription.get("credits_used", 0) / subscription.get("credits_limit")) * 100

        return schemas.TokenUsageResponse(
            tokens_used=subscription.get("credits_used", 0),
            tokens_remaining=subscription.get("credits_remaining", 0),
            tokens_limit=subscription.get("credits_limit", 0),
            percentage_used=round(percentage_used, 2),
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