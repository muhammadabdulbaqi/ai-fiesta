# Database Viewing Guide

This guide explains how to view and interact with the AI Fiesta PostgreSQL database.

## Quick Access Methods

### Method 1: Using pgAdmin (Recommended - You Already Have This!)

Since you mentioned you have pgAdmin installed, this is the easiest method:

1. **Open pgAdmin**

2. **Create a New Server Connection:**
   - Right-click "Servers" → "Create" → "Server"
   - **General Tab:**
     - Name: `AI Fiesta Local`
   - **Connection Tab:**
     - Host: `localhost`
     - Port: `5433` ⚠️ **Important: Use 5433, not 5432!**
     - Database: `fiesta_db`
     - Username: `fiesta_user`
     - Password: `fiesta_pass`
     - Check "Save password"
   - Click "Save"

3. **Browse the Database:**
   - Expand: `AI Fiesta Local` → `Databases` → `fiesta_db` → `Schemas` → `public` → `Tables`
   - You'll see tables like:
     - `users` - All registered users
     - `subscriptions` - User subscription tiers and usage
     - `conversations` - Chat conversation metadata
     - `messages` - Individual chat messages
     - `api_usage` - API call tracking
     - `cost_tracker` - Cost tracking per request

4. **View Data:**
   - Right-click any table → "View/Edit Data" → "All Rows"
   - Or write custom queries in the Query Tool

### Method 2: Using Docker psql (Command Line)

If you prefer command line:

```bash
# Connect to the database container
docker exec -it fiesta-db psql -U fiesta_user -d fiesta_db

# Once connected, you can run SQL queries:
# List all tables
\dt

# View users
SELECT * FROM users;

# View subscriptions
SELECT * FROM subscriptions;

# View conversations
SELECT * FROM conversations;

# View messages (first 10)
SELECT * FROM messages LIMIT 10;

# Exit
\q
```

### Method 3: Using a Database Client Tool

You can use any PostgreSQL client with these connection details:

- **Host:** `localhost`
- **Port:** `5433`
- **Database:** `fiesta_db`
- **Username:** `fiesta_user`
- **Password:** `fiesta_pass`

Popular tools:
- **DBeaver** (Free, cross-platform)
- **TablePlus** (Mac/Windows, paid)
- **DataGrip** (JetBrains, paid)
- **Postico** (Mac, paid)

### Method 4: Using Python Script

Create a simple Python script to query the database:

```python
# view_db.py
import asyncio
from sqlalchemy import text
from app.database import async_session_maker

async def view_data():
    async with async_session_maker() as session:
        # View users
        result = await session.execute(text("SELECT * FROM users"))
        users = result.fetchall()
        print("Users:", users)
        
        # View subscriptions
        result = await session.execute(text("SELECT * FROM subscriptions"))
        subs = result.fetchall()
        print("Subscriptions:", subs)

if __name__ == "__main__":
    asyncio.run(view_data())
```

Run it:
```bash
cd backend
python view_db.py
```

## Useful SQL Queries

### View All Users with Their Subscriptions
```sql
SELECT 
    u.id,
    u.email,
    u.username,
    s.tier,
    s.status,
    s.tokens_used,
    s.tokens_limit,
    s.credits_remaining,
    s.credits_limit
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id
ORDER BY u.created_at DESC;
```

### View Conversation Counts per User
```sql
SELECT 
    u.username,
    COUNT(c.id) as conversation_count,
    SUM((SELECT COUNT(*) FROM messages WHERE conversation_id = c.id)) as total_messages
FROM users u
LEFT JOIN conversations c ON u.id = c.user_id
GROUP BY u.id, u.username
ORDER BY conversation_count DESC;
```

### View Recent Messages
```sql
SELECT 
    m.id,
    m.role,
    LEFT(m.content, 50) as content_preview,
    m.created_at,
    c.title as conversation_title,
    u.username
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
JOIN users u ON c.user_id = u.id
ORDER BY m.created_at DESC
LIMIT 20;
```

### View Token Usage by User
```sql
SELECT 
    u.username,
    s.tier,
    s.tokens_used,
    s.tokens_limit,
    ROUND((s.tokens_used::float / s.tokens_limit * 100), 2) as usage_percent
FROM users u
JOIN subscriptions s ON u.id = s.user_id
ORDER BY usage_percent DESC;
```

### View Total Costs by Provider
```sql
SELECT 
    provider,
    COUNT(*) as request_count,
    SUM(cost) as total_cost,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(completion_tokens) as total_completion_tokens
FROM cost_tracker
GROUP BY provider
ORDER BY total_cost DESC;
```

## Database Schema Overview

### `users` Table
- `id` (UUID) - Primary key
- `email` (String) - User email
- `username` (String) - Username
- `hashed_password` (String) - Bcrypt hashed password
- `created_at` (Timestamp) - Account creation time

### `subscriptions` Table
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `tier` (String) - Subscription tier (free, pro, enterprise)
- `status` (String) - active, inactive, etc.
- `tokens_used` (Integer) - Tokens consumed this period
- `tokens_limit` (Integer) - Token limit for tier
- `credits_remaining` (Integer) - Available credits
- `credits_limit` (Integer) - Credit limit for tier
- `allowed_models` (JSON) - Array of allowed model names

### `conversations` Table
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `title` (String) - Conversation title
- `created_at` (Timestamp) - Creation time
- `updated_at` (Timestamp) - Last update time

### `messages` Table
- `id` (UUID) - Primary key
- `conversation_id` (UUID) - Foreign key to conversations
- `role` (String) - user, assistant, system
- `content` (Text) - Message content
- `model` (String) - Model used (if assistant message)
- `created_at` (Timestamp) - Message time

### `api_usage` Table
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `provider` (String) - openai, anthropic, gemini, etc.
- `model` (String) - Model name
- `prompt_tokens` (Integer)
- `completion_tokens` (Integer)
- `total_tokens` (Integer)
- `created_at` (Timestamp)

### `cost_tracker` Table
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `conversation_id` (UUID) - Foreign key to conversations
- `provider` (String) - Provider name
- `model` (String) - Model name
- `cost` (Float) - Cost in USD
- `prompt_tokens` (Integer)
- `completion_tokens` (Integer)
- `created_at` (Timestamp)

## Troubleshooting

### Can't Connect to Database
- **Check Docker is running:** `docker ps` (should see `fiesta-db`)
- **Check port:** Make sure you're using port `5433`, not `5432`
- **Check credentials:** Username `fiesta_user`, password `fiesta_pass`

### Database Not Found
- **Run migrations:** `cd backend && alembic upgrade head`
- **Check container logs:** `docker logs fiesta-db`

### Permission Denied
- Make sure you're using the correct username: `fiesta_user`
- The database should be accessible from localhost

## Quick Reference

**Connection String:**
```
postgresql://fiesta_user:fiesta_pass@localhost:5433/fiesta_db
```

**Docker Container:**
```bash
docker exec -it fiesta-db psql -U fiesta_user -d fiesta_db
```

**pgAdmin Connection:**
- Host: `localhost`
- Port: `5433`
- Database: `fiesta_db`
- Username: `fiesta_user`
- Password: `fiesta_pass`

