"""Script to create a regular user in the database."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_maker
from app.services import user_service


async def create_user():
    print("=" * 50)
    print("Create User")
    print("=" * 50)
    
    email = input("Email: ").strip()
    if not email:
        print("Email is required!")
        return
    
    username = input("Username: ").strip()
    if not username:
        print("Username is required!")
        return
    
    password = input("Password: ").strip()
    if not password:
        print("Password is required!")
        return
    
    tier = input("Subscription tier (free/pro/enterprise) [default: free]: ").strip().lower() or "free"
    if tier not in ["free", "pro", "enterprise"]:
        print("Invalid tier! Using 'free'")
        tier = "free"
    
    async with async_session_maker() as session:
        # Check if user exists
        existing_email = await user_service.get_user_by_email(session, email)
        if existing_email:
            print(f"❌ User with email {email} already exists!")
            return
        
        existing_username = await user_service.get_user_by_username(session, username)
        if existing_username:
            print(f"❌ User with username {username} already exists!")
            return
        
        # Create user
        user = await user_service.create_user(session, email, username, password, tier)
        print("\n" + "=" * 50)
        print("✅ User created successfully!")
        print("=" * 50)
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Username: {user.username}")
        print(f"Tier: {tier}")
        print(f"\nUser can now login at http://localhost:3000/login")


if __name__ == "__main__":
    try:
        asyncio.run(create_user())
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

