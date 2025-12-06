from fastapi import APIRouter, HTTPException
from datetime import datetime

from .. import schemas, models
from ..dependencies import get_user_or_404, get_subscription_or_404_by_user

router = APIRouter(prefix="", tags=["Subscriptions"])


@router.get("/subscriptions/{user_id}", response_model=schemas.SubscriptionDetail)
async def get_user_subscription(user_id: str):
    """Get subscription details for a user"""
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
        monthly_cost_usd=subscription["monthly_cost_usd"],
        monthly_api_cost_usd=subscription["monthly_api_cost_usd"],
        requests_this_minute=0,  # TODO: implement rate limiter tracking
        status=subscription["status"],
        created_at=subscription["created_at"],
        expires_at=subscription.get("expires_at"),
    )


@router.post("/subscriptions/{user_id}/upgrade", response_model=schemas.SubscriptionDetail)
async def upgrade_subscription(user_id: str, tier: str = "pro"):
    """Upgrade user to a different tier (free, pro, enterprise)"""
    user = get_user_or_404(user_id)
    if tier not in models.SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}. Available: {list(models.SUBSCRIPTION_TIERS.keys())}")
    
    # Find existing subscription
    old_sub = get_subscription_or_404_by_user(user_id)
    
    # Delete old and create new
    del models.subscriptions_db[old_sub["id"]]
    new_sub = models.create_default_subscription(user_id, tier)
    
    return schemas.SubscriptionDetail(
        id=new_sub["id"],
        user_id=new_sub["user_id"],
        tier_id=new_sub["tier_id"],
        tier_name=new_sub["tier_name"],
        allowed_models=new_sub["allowed_models"],
        tokens_limit=new_sub["tokens_limit"],
        tokens_used=new_sub["tokens_used"],
        tokens_remaining=new_sub["tokens_remaining"],
        monthly_cost_usd=new_sub["monthly_cost_usd"],
        monthly_api_cost_usd=new_sub["monthly_api_cost_usd"],
        requests_this_minute=0,
        status=new_sub["status"],
        created_at=new_sub["created_at"],
        expires_at=new_sub.get("expires_at"),
    )


@router.post("/subscriptions/{user_id}/add-tokens")
async def add_tokens(user_id: str, tokens: int):
    """Grant additional tokens to a user (admin action)"""
    if tokens <= 0:
        raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    user = get_user_or_404(user_id)
    subscription = get_subscription_or_404_by_user(user_id)
    
    subscription["tokens_remaining"] += tokens
    subscription["tokens_limit"] += tokens
    
    return {
        "message": f"Added {tokens} tokens to user",
        "tokens_remaining": subscription["tokens_remaining"],
        "tokens_limit": subscription["tokens_limit"],
    }


@router.put("/subscriptions/{user_id}/use-tokens", response_model=schemas.TokenUsageResponse)
async def use_tokens(user_id: str, tokens: int):
    """Deduct tokens from a user's subscription"""
    if tokens <= 0:
        raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    user = get_user_or_404(user_id)
    subscription = get_subscription_or_404_by_user(user_id)
    
    if subscription["tokens_remaining"] < tokens:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient tokens. Required: {tokens}, Available: {subscription['tokens_remaining']}",
        )
    
    subscription["tokens_used"] += tokens
    subscription["tokens_remaining"] -= tokens
    
    percentage_used = (subscription["tokens_used"] / subscription["tokens_limit"]) * 100
    
    return schemas.TokenUsageResponse(
        tokens_used=subscription["tokens_used"],
        tokens_remaining=subscription["tokens_remaining"],
        tokens_limit=subscription["tokens_limit"],
        percentage_used=round(percentage_used, 2),
    )


@router.get("/subscriptions/")
async def list_available_tiers():
    """List all available subscription tiers"""
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

