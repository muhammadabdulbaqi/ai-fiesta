# Database Management Guide

This guide explains how to manage the AI Fiesta database, including viewing data, adding users, and creating admin accounts.

## Prerequisites

- PostgreSQL database running (via Docker or local installation)
- Database connection details:
  - Host: `localhost`
  - Port: `5433` (Docker) or `5432` (local)
  - Database: `fiesta_db`
  - Username: `fiesta_user`
  - Password: `fiesta_pass`

## Viewing the Database

### Option 1: Using pgAdmin (Recommended)

1. **Download and Install pgAdmin**
   - Download from: https://www.pgadmin.org/download/
   - Install and launch pgAdmin

2. **Connect to Database**
   - Right-click "Servers" → "Create" → "Server"
   - **General Tab:**
     - Name: `AI Fiesta DB`
   - **Connection Tab:**
     - Host: `localhost`
     - Port: `5433` (or `5432` if not using Docker)
     - Database: `fiesta_db`
     - Username: `fiesta_user`
     - Password: `fiesta_pass`
     - Check "Save password"
   - Click "Save"

3. **Browse Tables**
   - Expand: `AI Fiesta DB` → `Databases` → `fiesta_db` → `Schemas` → `public` → `Tables`
   - Right-click any table → "View/Edit Data" → "All Rows"

### Option 2: Using psql Command Line

```bash
# Connect to database
psql -h localhost -p 5433 -U fiesta_user -d fiesta_db

# Enter password when prompted: fiesta_pass
```

### Option 3: Using Python Script

Create a script `view_db.py`:

```python
import asyncio
from sqlalchemy import select
from app.database import async_session_maker
from app.db_models import User, AdminUser, Subscription, Conversation, Message

async def view_users():
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            print(f"User: {user.username} ({user.email}) - ID: {user.id}")

async def view_admins():
    async with async_session_maker() as session:
        result = await session.execute(select(AdminUser))
        admins = result.scalars().all()
        for admin in admins:
            print(f"Admin: {admin.username} ({admin.email}) - ID: {admin.id}")

if __name__ == "__main__":
    asyncio.run(view_users())
    asyncio.run(view_admins())
```

## Adding Users

### Method 1: Through the Frontend (Recommended)

1. Navigate to `http://localhost:3000/register`
2. Fill in:
   - Email
   - Username
   - Password
3. Click "Sign up"
4. User will be automatically created with a default "free" tier subscription

### Method 2: Directly in Database (pgAdmin)

1. Open pgAdmin and connect to the database
2. Navigate to `Tables` → `users`
3. Right-click → "View/Edit Data" → "All Rows"
4. Click the "+" button to add a new row
5. **Note:** You'll need to hash the password manually (see Method 3)

### Method 3: Using Python Script

Create a script `add_user.py`:

```python
import asyncio
from app.database import async_session_maker
from app.services import user_service, auth_service

async def create_user():
    email = input("Email: ")
    username = input("Username: ")
    password = input("Password: ")
    
    async with async_session_maker() as session:
        # Check if user exists
        existing = await user_service.get_user_by_email(session, email)
        if existing:
            print("User already exists!")
            return
        
        # Create user
        user = await user_service.create_user(session, email, username, password)
        print(f"User created: {user.username} ({user.email}) - ID: {user.id}")

if __name__ == "__main__":
    asyncio.run(create_user())
```

Run it:
```bash
cd backend
python add_user.py
```

## Creating Admin Users

### Method 1: Using Python Script (Recommended)

Create a script `create_admin.py` in the `backend` folder:

```python
import asyncio
from app.database import async_session_maker
from app.services import admin_service, auth_service

async def create_admin():
    email = input("Admin Email: ")
    username = input("Admin Username: ")
    password = input("Admin Password: ")
    
    async with async_session_maker() as session:
        # Check if admin exists
        existing = await admin_service.get_admin_by_email(session, email)
        if existing:
            print("Admin already exists!")
            return
        
        # Hash password
        hashed_password = auth_service.hash_password(password)
        
        # Create admin
        admin = await admin_service.create_admin(session, email, username, hashed_password)
        print(f"Admin created: {admin.username} ({admin.email}) - ID: {admin.id}")
        print(f"\nYou can now login at http://localhost:3000/login with:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")

if __name__ == "__main__":
    asyncio.run(create_admin())
```

Run it:
```bash
cd backend
python create_admin.py
```

### Method 2: Directly in Database (pgAdmin)

1. Open pgAdmin → `Tables` → `admin_users`
2. Right-click → "View/Edit Data" → "All Rows"
3. Click "+" to add a new row
4. Fill in:
   - `id`: Leave empty (auto-generated)
   - `email`: Admin email
   - `username`: Admin username
   - `hashed_password`: **You need to hash the password first** (see below)
   - `is_active`: `true`
   - `created_at`: Leave empty (auto-generated)

**To hash password:**
```python
from app.services import auth_service
hashed = auth_service.hash_password("your-password")
print(hashed)  # Copy this value
```

## Useful SQL Queries

### View All Users
```sql
SELECT id, email, username, is_active, created_at FROM users;
```

### View All Admins
```sql
SELECT id, email, username, is_active, created_at FROM admin_users;
```

### View User Subscriptions
```sql
SELECT 
    u.username,
    s.tier_name,
    s.tokens_used,
    s.tokens_remaining,
    s.credits_used,
    s.credits_remaining,
    s.status
FROM subscriptions s
JOIN users u ON s.user_id = u.id;
```

### View Conversations
```sql
SELECT 
    c.id,
    u.username,
    c.title,
    c.created_at,
    COUNT(m.id) as message_count
FROM conversations c
JOIN users u ON c.user_id = u.id
LEFT JOIN messages m ON m.conversation_id = c.id
GROUP BY c.id, u.username, c.title, c.created_at
ORDER BY c.created_at DESC;
```

### View API Usage
```sql
SELECT 
    u.username,
    au.provider,
    au.calls,
    au.total_tokens,
    au.cost_usd
FROM api_usage au
JOIN users u ON au.user_id = u.id
ORDER BY au.cost_usd DESC;
```

## Running Migrations

After creating the AdminUser model, run migrations:

```bash
cd backend
alembic upgrade head
```

This will create the `admin_users` table if it doesn't exist.

## Resetting the Database

**⚠️ WARNING: This will delete all data!**

```bash
cd backend
alembic downgrade base
alembic upgrade head
```

Or manually drop tables in pgAdmin:
1. Right-click table → "Delete/Drop"
2. Check "Cascade" to delete related data
3. Click "OK"

## Common Tasks

### Change User Password
```python
import asyncio
from app.database import async_session_maker
from app.services import user_service, auth_service
from sqlalchemy import select
from app.db_models import User

async def change_password():
    email = input("User email: ")
    new_password = input("New password: ")
    
    async with async_session_maker() as session:
        user = await user_service.get_user_by_email(session, email)
        if not user:
            print("User not found!")
            return
        
        user.hashed_password = auth_service.hash_password(new_password)
        await session.commit()
        print("Password updated!")

if __name__ == "__main__":
    asyncio.run(change_password())
```

### Add Credits to User
```python
import asyncio
from app.database import async_session_maker
from app.services import user_service

async def add_credits():
    email = input("User email: ")
    credits = int(input("Credits to add: "))
    
    async with async_session_maker() as session:
        user = await user_service.get_user_by_email(session, email)
        if not user:
            print("User not found!")
            return
        
        sub = await user_service.get_subscription(session, user.id)
        if sub:
            sub.credits_remaining += credits
            sub.credits_limit += credits
            await session.commit()
            print(f"Added {credits} credits. New total: {sub.credits_remaining}")

if __name__ == "__main__":
    asyncio.run(add_credits())
```

## Troubleshooting

### Can't Connect to Database
- Check if Docker container is running: `docker ps`
- Verify port: `5433` for Docker, `5432` for local
- Check connection string in `backend/.env`

### Migration Errors
- Make sure you're in the `backend` directory
- Check that `DATABASE_URL` in `.env` is correct
- Try: `alembic current` to see current migration

### Password Hashing Issues
- Always use `auth_service.hash_password()` from Python
- Never store plain text passwords
- Bcrypt hashes start with `$2b$` or `$2a$`

