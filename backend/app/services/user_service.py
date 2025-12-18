"""User and subscription database operations"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db_models import User, Subscription
from app import models as app_models


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, username: str, password: str, tier: str = "free") -> User:
    """Create new user with default subscription"""
    from app.services import auth_service
    
    user = User(
        email=email,
        username=username,
        hashed_password=auth_service.hash_password(password),
        is_active=True,
    )
    db.add(user)
    await db.flush()  # Get user.id
    
    # Create default subscription
    tier_info = app_models.SUBSCRIPTION_TIERS[tier]
    subscription = Subscription(
        user_id=user.id,
        tier_id=tier_info["tier_id"],
        tier_name=tier_info["name"],
        plan_type=tier,
        allowed_models=tier_info["allowed_models"],
        tokens_limit=tier_info["tokens_per_month"],
        tokens_used=0,
        tokens_remaining=tier_info["tokens_per_month"],
        credits_limit=tier_info.get("credits_per_month", tier_info["tokens_per_month"]),
        credits_used=0,
        credits_remaining=tier_info.get("credits_per_month", tier_info["tokens_per_month"]),
        monthly_cost_usd=tier_info["cost_usd"],
        monthly_api_cost_usd=0.0,
        rate_limit_per_minute=tier_info["rate_limit_per_minute"],
    )
    db.add(subscription)
    
    await db.commit()
    await db.refresh(user)
    await db.refresh(subscription)
    
    return user


async def get_subscription(db: AsyncSession, user_id: str) -> Optional[Subscription]:
    """Get user's subscription"""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def deduct_credits_atomic(
    db: AsyncSession,
    user_id: str,
    credits: int
) -> Subscription:
    """
    Atomically deduct credits using SELECT FOR UPDATE.
    Prevents race conditions from concurrent requests.
    """
    # Lock the row for update
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .with_for_update()
    )
    subscription = result.scalar_one()
    
    # Check if sufficient credits
    if subscription.credits_remaining < credits:
        raise ValueError(
            f"Insufficient credits: need {credits}, have {subscription.credits_remaining}"
        )
    
    # Deduct credits
    subscription.credits_used += credits
    subscription.credits_remaining -= credits
    
    await db.commit()
    await db.refresh(subscription)
    
    return subscription