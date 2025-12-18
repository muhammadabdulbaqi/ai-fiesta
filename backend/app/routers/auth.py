"""Authentication routes for user registration and login."""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.services import user_service, auth_service, admin_service
from app.db_models import User, Subscription
from app import models

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    username: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user from JWT token. Supports both regular users and admins."""
    token = credentials.credentials
    payload = auth_service.decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    role = payload.get("role")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # If admin, try to find a regular user account with the same email
    if role == "admin":
        admin = await admin_service.get_admin_by_id(db, user_id)
        if admin:
            # Look for a regular user with the same email
            user = await user_service.get_user_by_email(db, admin.email)
            if user:
                return user
            # If no regular user exists, create one automatically for the admin
            # This allows admins to use the regular UI
            from app.db_models import Subscription
            from app import models
            import uuid
            from datetime import datetime
            
            new_user = User(
                id=str(uuid.uuid4()),
                email=admin.email,
                username=admin.username,
                hashed_password=admin.hashed_password,  # Same password hash
                is_active=True,
                created_at=datetime.now()
            )
            db.add(new_user)
            await db.flush()
            
            # Create default subscription
            tier = models.SUBSCRIPTION_TIERS["free"]
            subscription = Subscription(
                user_id=new_user.id,
                tier_id=tier["tier_id"],
                tier_name=tier["name"],
                plan_type="free",
                allowed_models=tier["allowed_models"],
                tokens_limit=tier["tokens_per_month"],
                tokens_used=0,
                tokens_remaining=tier["tokens_per_month"],
                credits_limit=tier["credits_per_month"],
                credits_used=0,
                credits_remaining=tier["credits_per_month"],
                monthly_cost_usd=tier.get("cost_usd", 0.0),
                monthly_api_cost_usd=0.0,
                rate_limit_per_minute=tier.get("rate_limit_per_minute", 5),
                status="active",
                created_at=datetime.now()
            )
            db.add(subscription)
            await db.commit()
            await db.refresh(new_user)
            return new_user
    
    # Regular user lookup
    user = await user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = await user_service.get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_username = await user_service.get_user_by_username(db, request.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    hashed_password = auth_service.hash_password(request.password)
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    
    # Create default subscription
    tier = models.SUBSCRIPTION_TIERS["free"]
    subscription = Subscription(
        user_id=user.id,
        tier_id=tier["tier_id"],
        tier_name=tier["name"],
        plan_type="free",
        allowed_models=tier["allowed_models"],
        tokens_limit=tier["tokens_per_month"],
        tokens_used=0,
        tokens_remaining=tier["tokens_per_month"],
        credits_limit=tier.get("credits_per_month", tier["tokens_per_month"]),
        credits_used=0,
        credits_remaining=tier.get("credits_per_month", tier["tokens_per_month"]),
        monthly_cost_usd=tier["cost_usd"],
        rate_limit_per_minute=tier["rate_limit_per_minute"],
    )
    db.add(subscription)
    
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    access_token = auth_service.create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        username=user.username,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get access token. Checks admin users first, then regular users."""
    # First check if it's an admin user
    admin = await admin_service.get_admin_by_email(db, request.email)
    if admin:
        if not auth_service.verify_password(request.password, admin.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is inactive"
            )
        
        # Create admin access token with role
        access_token = auth_service.create_access_token(data={"sub": admin.id, "role": "admin"})
        
        return TokenResponse(
            access_token=access_token,
            user_id=admin.id,
            email=admin.email,
            username=admin.username,
        )
    
    # If not admin, check regular user
    user = await user_service.get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not auth_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create regular user access token
    access_token = auth_service.create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        username=user.username,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
    )

