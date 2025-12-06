from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid

from .. import schemas, models

router = APIRouter(prefix="", tags=["Users"])


@router.post("/users/", response_model=schemas.UserResponse, status_code=201)
async def create_user(user: schemas.UserCreate):
    # Check for existing email or username
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
async def list_users():
    return [schemas.UserResponse(**u) for u in models.users_db.values()]


@router.get("/users/{user_id}", response_model=schemas.UserResponse)
async def get_user(user_id: str):
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return schemas.UserResponse(**models.users_db[user_id])


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str):
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")
    # delete subscriptions
    subs = [sid for sid, s in models.subscriptions_db.items() if s["user_id"] == user_id]
    for sid in subs:
        del models.subscriptions_db[sid]
    del models.users_db[user_id]
    return None


@router.get("/users/{user_id}/tokens", response_model=schemas.TokenUsageResponse)
async def get_user_tokens(user_id: str):
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")

    user_subscription = None
    for sub in models.subscriptions_db.values():
        if sub["user_id"] == user_id:
            user_subscription = sub
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
