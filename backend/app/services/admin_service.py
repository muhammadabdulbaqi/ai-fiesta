"""Admin user database operations"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db_models import AdminUser


async def get_admin_by_id(db: AsyncSession, admin_id: str) -> Optional[AdminUser]:
    """Get admin user by ID"""
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    return result.scalar_one_or_none()


async def get_admin_by_email(db: AsyncSession, email: str) -> Optional[AdminUser]:
    """Get admin user by email"""
    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    return result.scalar_one_or_none()


async def get_admin_by_username(db: AsyncSession, username: str) -> Optional[AdminUser]:
    """Get admin user by username"""
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    return result.scalar_one_or_none()


async def create_admin(db: AsyncSession, email: str, username: str, hashed_password: str) -> AdminUser:
    """Create new admin user"""
    admin = AdminUser(
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    
    return admin

