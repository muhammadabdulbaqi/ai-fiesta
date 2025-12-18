# Adding Users via pgAdmin

Yes, you can add users and admins directly through pgAdmin! However, there are some important steps to follow.

## Understanding the Error

The error you saw (`DuplicateTableError: relation "admin_users" already exists`) happened because:
1. The `admin_users` table was already created (probably by `init_db()` when the backend started)
2. Alembic didn't know about it, so it tried to create it again during migration
3. The migration has been fixed to be idempotent (it now checks if the table exists first)

## Adding Users via pgAdmin

### Prerequisites
1. **pgAdmin installed** - Download from https://www.pgadmin.org/download/
2. **Connected to database** - See `DATABASE_MANAGEMENT_GUIDE.md` for connection details

### Method 1: Using pgAdmin UI (Easiest)

#### For Regular Users:

1. **Open pgAdmin** and connect to your database
2. Navigate to: `Servers` → `AI Fiesta DB` → `Databases` → `fiesta_db` → `Schemas` → `public` → `Tables` → `users`
3. Right-click `users` → **"View/Edit Data"** → **"All Rows"**
4. Click the **"+"** button (Add Row) at the bottom
5. Fill in the fields:
   - **`id`**: Generate a UUID (see below)
   - **`email`**: User's email (e.g., `user@example.com`)
   - **`username`**: Username (e.g., `newuser`)
   - **`hashed_password`**: **IMPORTANT** - You must hash the password first (see below)
   - **`is_active`**: `true`
   - **`created_at`**: Leave empty (auto-generated) or set to current timestamp
6. Click **"Save"**

#### For Admin Users:

1. Navigate to: `Tables` → `admin_users`
2. Right-click `admin_users` → **"View/Edit Data"** → **"All Rows"**
3. Click **"+"** button
4. Fill in the same fields as above
5. Click **"Save"**

### Method 2: Using SQL Query (More Control)

#### Generate UUID and Hash Password

First, you need to:
1. **Generate a UUID** for the `id` field
2. **Hash the password** using bcrypt

**Option A: Use Python Script**

Create a temporary script `hash_password.py`:

```python
import bcrypt
import uuid

password = input("Enter password: ")
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
user_id = str(uuid.uuid4())

print(f"\nUser ID: {user_id}")
print(f"Hashed Password: {hashed}")
```

Run it:
```bash
cd backend
python hash_password.py
```

**Option B: Use Online Tools (Less Secure)**
- UUID Generator: https://www.uuidgenerator.net/
- Bcrypt Hash Generator: https://bcrypt-generator.com/ (use 12 rounds)

#### Insert User via SQL

In pgAdmin, open **Query Tool** (Tools → Query Tool) and run:

**For Regular User:**
```sql
INSERT INTO users (id, email, username, hashed_password, is_active, created_at)
VALUES (
    'YOUR_UUID_HERE',                    -- Replace with generated UUID
    'user@example.com',                  -- User's email
    'newuser',                            -- Username
    '$2b$12$YOUR_HASHED_PASSWORD_HERE',  -- Replace with hashed password
    true,                                 -- is_active
    NOW()                                 -- created_at
);
```

**For Admin User:**
```sql
INSERT INTO admin_users (id, email, username, hashed_password, is_active, created_at)
VALUES (
    'YOUR_UUID_HERE',
    'admin@example.com',
    'admin',
    '$2b$12$YOUR_HASHED_PASSWORD_HERE',
    true,
    NOW()
);
```

**Create Subscription for Regular User:**

After creating a user, you need to create their subscription:

```sql
INSERT INTO subscriptions (
    id, 
    user_id, 
    tier_id, 
    tier_name, 
    plan_type, 
    allowed_models, 
    tokens_limit, 
    tokens_used, 
    tokens_remaining, 
    credits_limit, 
    credits_used, 
    credits_remaining, 
    monthly_cost_usd, 
    monthly_api_cost_usd, 
    rate_limit_per_minute, 
    status, 
    created_at
)
VALUES (
    gen_random_uuid()::text,              -- Subscription ID
    'YOUR_USER_ID_HERE',                  -- The user ID you just created
    'free',                                -- Tier ID
    'Free',                                -- Tier name
    'free',                                -- Plan type
    '["gemini-2.5-flash", "gpt-3.5-turbo"]'::json,  -- Allowed models
    5000,                                  -- Tokens limit
    0,                                     -- Tokens used
    5000,                                  -- Tokens remaining
    5000,                                  -- Credits limit
    0,                                     -- Credits used
    5000,                                  -- Credits remaining
    0.0,                                   -- Monthly cost
    0.0,                                   -- Monthly API cost
    5,                                     -- Rate limit per minute
    'active',                              -- Status
    NOW()                                  -- Created at
);
```

## Important Notes

### Password Hashing
- **NEVER** store plain text passwords
- Always use bcrypt with 12 rounds
- The hash should start with `$2b$12$` or `$2a$12$`
- Use the Python script or the provided `create_admin.py` / `add_user.py` scripts for proper hashing

### UUID Generation
- Use `uuid.uuid4()` in Python or an online UUID generator
- The ID must be a valid UUID string

### Required Fields
- **`id`**: UUID string (required)
- **`email`**: Must be unique (required)
- **`username`**: Must be unique (required)
- **`hashed_password`**: Bcrypt hash (required)
- **`is_active`**: Boolean, default `true` (required)
- **`created_at`**: Timestamp, can be `NOW()` or left empty (optional)

### For Regular Users Only
- After creating a user, you **must** create a subscription record
- Use the SQL query above or the `add_user.py` script (which does this automatically)

## Recommended Approach

**For most cases, use the Python scripts:**
- `python create_admin.py` - Creates admin users
- `python add_user.py` - Creates regular users with subscriptions

**Why?**
- Automatically handles password hashing
- Generates UUIDs
- Creates subscriptions for regular users
- Validates email/username uniqueness
- Sets proper timestamps

**Use pgAdmin when:**
- You need to bulk import users
- You're doing data migrations
- You're fixing data issues
- You're comfortable with SQL

## Troubleshooting

### "Duplicate key value violates unique constraint"
- Email or username already exists
- Check existing users: `SELECT email, username FROM users;`

### "Password doesn't work after adding user"
- Make sure you hashed the password correctly
- The hash should be the full bcrypt hash, not just the password

### "User can't login"
- Check `is_active` is `true`
- Verify the password hash is correct
- Make sure the user has a subscription (for regular users)

### "Foreign key constraint violation"
- When creating a subscription, make sure the `user_id` exists in the `users` table

