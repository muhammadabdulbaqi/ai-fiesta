from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from .. import schemas, models
from ..config import settings
from ..database import get_db
from ..db_models import User
from ..services import user_service

router = APIRouter(prefix="", tags=["Users"])


@router.post("/users/", response_model=schemas.UserResponse, status_code=201)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    if settings.use_database:
        # DB Check existing
        existing_email = await user_service.get_user_by_email(db, user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # We need a check for username too, simplistic approach here:
        q = await db.execute(select(User).where(User.username == user.username))
        if q.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already taken")

        # Create in DB
        new_user = await user_service.create_user(db, user.email, user.username, user.password)
        return new_user
    else:
        # Legacy In-Memory
        for existing_user in models.users_db.values():
            if existing_user["email"] == user.email:
                raise HTTPException(status_code=400, detail="Email already registered")
            if existing_user["username"] == user.username:
                raise HTTPException(status_code=400, detail="Username already taken")

        user_id = str(uuid.uuid4())
        new_user = {
            "id": user_id,
            "email": user.email,
            "username": user.username,
            "hashed_password": f"hashed_{user.password}",
            "is_active": True,
            "created_at": datetime.now(),
        }
        models.users_db[user_id] = new_user
        models.create_default_subscription(user_id, "free")
        return schemas.UserResponse(**new_user)


@router.get("/users/", response_model=list[schemas.UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    if settings.use_database:
        result = await db.execute(select(User))
        return result.scalars().all()
    else:
        return [schemas.UserResponse(**u) for u in models.users_db.values()]


@router.get("/users/{user_id}", response_model=schemas.UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    if settings.use_database:
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    else:
        if user_id not in models.users_db:
            raise HTTPException(status_code=404, detail="User not found")
        return schemas.UserResponse(**models.users_db[user_id])


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    if settings.use_database:
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await db.delete(user)
        await db.commit()
    else:
        if user_id not in models.users_db:
            raise HTTPException(status_code=404, detail="User not found")
        # delete subscriptions
        subs = [sid for sid, s in models.subscriptions_db.items() if s["user_id"] == user_id]
        for sid in subs:
            del models.subscriptions_db[sid]
        del models.users_db[user_id]
    return None


@router.get("/users/{user_id}/tokens", response_model=schemas.TokenUsageResponse)
async def get_user_tokens(user_id: str, db: AsyncSession = Depends(get_db)):
    if settings.use_database:
        sub = await user_service.get_subscription(db, user_id)
        if not sub:
             raise HTTPException(status_code=404, detail="Subscription not found")
        
        limit = sub.tokens_limit or 1
        percentage = (sub.tokens_used / limit) * 100
        
        return schemas.TokenUsageResponse(
            tokens_used=sub.tokens_used,
            tokens_remaining=sub.tokens_remaining,
            tokens_limit=sub.tokens_limit,
            percentage_used=round(percentage, 2),
            credits_used=sub.credits_used,
            credits_remaining=sub.credits_remaining
        )
    else:
        # Legacy
        if user_id not in models.users_db:
            raise HTTPException(status_code=404, detail="User not found")

        user_subscription = None
        for s in models.subscriptions_db.values():
            if s["user_id"] == user_id:
                user_subscription = s
                break

        if not user_subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        percentage_used = (user_subscription["tokens_used"] / user_subscription["tokens_limit"]) * 100

        return schemas.TokenUsageResponse(
            tokens_used=user_subscription["tokens_used"],
            tokens_remaining=user_subscription["tokens_remaining"],
            tokens_limit=user_subscription["tokens_limit"],
            percentage_used=round(percentage_used, 2),
        )