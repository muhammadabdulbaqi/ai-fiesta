"""Script to create an admin user in the database."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_maker
from app.services import admin_service, auth_service


async def create_admin():
    print("=" * 50)
    print("Create Admin User")
    print("=" * 50)
    
    email = input("Admin Email: ").strip()
    if not email:
        print("Email is required!")
        return
    
    username = input("Admin Username: ").strip()
    if not username:
        print("Username is required!")
        return
    
    password = input("Admin Password: ").strip()
    if not password:
        print("Password is required!")
        return
    
    async with async_session_maker() as session:
        # Check if admin exists
        existing_email = await admin_service.get_admin_by_email(session, email)
        if existing_email:
            print(f"❌ Admin with email {email} already exists!")
            return
        
        existing_username = await admin_service.get_admin_by_username(session, username)
        if existing_username:
            print(f"❌ Admin with username {username} already exists!")
            return
        
        # Hash password
        hashed_password = auth_service.hash_password(password)
        
        # Create admin
        admin = await admin_service.create_admin(session, email, username, hashed_password)
        print("\n" + "=" * 50)
        print("✅ Admin created successfully!")
        print("=" * 50)
        print(f"ID: {admin.id}")
        print(f"Email: {admin.email}")
        print(f"Username: {admin.username}")
        print(f"\nYou can now login at http://localhost:3000/login with:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print("\nAfter login, you'll see the 'Admin Dashboard' link in the sidebar.")


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

