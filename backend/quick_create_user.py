"""Quick script to create a regular user account (simpler than admin)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_maker
from app.services import user_service


async def create_user():
    """Create a regular user account."""
    print("=" * 50)
    print("Create Regular User Account")
    print("=" * 50)
    print()
    print("Enter user details (or press Enter to use defaults):")
    
    email = input("Email [user@example.com]: ").strip() or "user@example.com"
    username = input("Username [testuser]: ").strip() or "testuser"
    password = input("Password [test123]: ").strip() or "test123"
    
    async with async_session_maker() as session:
        # Check if user exists
        existing_email = await user_service.get_user_by_email(session, email)
        if existing_email:
            print(f"User with email {email} already exists!")
            return
        
        existing_username = await user_service.get_user_by_username(session, username)
        if existing_username:
            print(f"User with username {username} already exists!")
            return
        
        # Create user
        user = await user_service.create_user(session, email, username, password, "free")
        print()
        print("=" * 50)
        print("User created successfully!")
        print("=" * 50)
        print(f"Email: {email}")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print()
        print("You can now login at http://localhost:3000/login")


if __name__ == "__main__":
    try:
        asyncio.run(create_user())
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

