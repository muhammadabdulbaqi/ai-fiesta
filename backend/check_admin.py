"""Simple script to check if admin users exist in the database."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_maker
from app.services import admin_service
from sqlalchemy import select, func
from app.db_models import AdminUser


async def check_admins():
    """Check if any admin users exist in the database."""
    async with async_session_maker() as session:
        # Count admins
        result = await session.execute(select(func.count(AdminUser.id)))
        count = result.scalar()
        
        print("=" * 50)
        print("Admin Users Check")
        print("=" * 50)
        print(f"Total admin users: {count}")
        print()
        
        if count == 0:
            print("No admin users found in the database.")
            print()
            print("To create an admin user, run:")
            print("  python create_admin.py")
        else:
            # List all admins
            result = await session.execute(select(AdminUser))
            admins = result.scalars().all()
            
            print("Admin users found:")
            for admin in admins:
                print(f"  - ID: {admin.id}")
                print(f"    Email: {admin.email}")
                print(f"    Username: {admin.username}")
                print(f"    Active: {admin.is_active}")
                print(f"    Created: {admin.created_at}")
                print()


if __name__ == "__main__":
    try:
        asyncio.run(check_admins())
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

