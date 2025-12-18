"""Admin authentication routes."""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.services import admin_service, auth_service
from app.db_models import AdminUser

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])
security = HTTPBearer()


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str
    email: str
    username: str


class AdminUserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """Dependency to get current authenticated admin from JWT token."""
    token = credentials.credentials
    payload = auth_service.decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if token has admin role
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin_id = payload.get("sub")
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin = await admin_service.get_admin_by_id(db, admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return admin


@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(request: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    """Admin login and get access token."""
    admin = await admin_service.get_admin_by_email(db, request.email)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
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
    
    # Create access token with admin role
    access_token = auth_service.create_access_token(data={"sub": admin.id, "role": "admin"})
    
    return AdminTokenResponse(
        access_token=access_token,
        admin_id=admin.id,
        email=admin.email,
        username=admin.username,
    )


@router.get("/me", response_model=AdminUserResponse)
async def get_current_admin_info(current_admin: AdminUser = Depends(get_current_admin)):
    """Get current authenticated admin information."""
    return AdminUserResponse(
        id=current_admin.id,
        email=current_admin.email,
        username=current_admin.username,
        is_active=current_admin.is_active,
    )

