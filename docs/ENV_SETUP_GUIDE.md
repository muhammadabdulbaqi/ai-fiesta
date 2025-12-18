# Environment Variables Setup Guide

## Where to Put `.env` Files

### Backend `.env` File
**Location:** `backend/.env` (NOT in root)

**Why?** 
- The backend code runs from the `backend/` directory
- When you run `uvicorn main:app`, it looks for `.env` in the current working directory
- Alembic migrations also run from `backend/` and look for `.env` there

**How to create:**
```bash
# From project root
cd backend
copy "..\.env sample" .env
# Or manually create backend/.env
```

### Frontend `.env.local` File
**Location:** `frontend/.env.local` (NOT in root)

**Why?**
- Next.js looks for `.env.local` in the `frontend/` directory
- This is where the frontend runs from

**How to create:**
```bash
# From project root
cd frontend
# Create .env.local with:
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

## What is JWT_SECRET_KEY?

**JWT_SECRET_KEY** is a secret string used to sign and verify JSON Web Tokens (JWTs) for authentication.

### What it does:
- **Signs tokens:** When a user logs in, the backend creates a JWT token signed with this secret
- **Verifies tokens:** When a user makes an authenticated request, the backend verifies the token using this secret
- **Security:** If someone knows your secret key, they could forge tokens and impersonate users!

### Important Security Rules:
1. ✅ **Never commit `.env` to git** (it's already in `.gitignore`)
2. ✅ **Use a strong, random secret** in production
3. ✅ **Never share your secret key** publicly
4. ✅ **Use different secrets** for development and production

### How to Generate a Secure Secret Key

**Option 1: Using Python (Recommended)**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Option 2: Using OpenSSL**
```bash
openssl rand -base64 32
```

**Option 3: Using PowerShell (Windows)**
```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

**Option 4: Online Generator**
- Visit: https://generate-secret.vercel.app/32
- Or: https://www.allkeysgenerator.com/Random/Security-Encryption-Key-Generator.aspx

### Example:
```ini
# Development (you can use a simple one)
JWT_SECRET_KEY=dev-secret-key-change-in-production-12345

# Production (use a generated secure key)
JWT_SECRET_KEY=K8j3mN9pQ2rS5tV7wX0yZ1aB3cD5eF7gH9iJ1kL3mN5oP7qR9sT1uV3wX5yZ
```

## Complete `.env` File Setup

### Step 1: Create `backend/.env`

```bash
cd backend
# Copy the sample
copy "..\.env sample" .env
```

### Step 2: Edit `backend/.env`

Open `backend/.env` and fill in:

```ini
# App Settings
APP_NAME=LLM Streaming Backend API
VERSION=0.1.0
DOCS_URL=/docs
REDOC_URL=/redoc
CORS_ALLOW_ORIGINS=["*"]

# API Keys (add at least one!)
OPENAI_API_KEY=sk-your-openai-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
# OR
GEMINI_API_KEY=your-gemini-key-here
# Optional
GROK_API_KEY=your-grok-key-here
PERPLEXITY_API_KEY=your-perplexity-key-here

# Database (already configured for Docker)
DATABASE_URL=postgresql+asyncpg://fiesta_user:fiesta_pass@localhost:5433/fiesta_db

# JWT Authentication
# Generate a secure key using one of the methods above!
JWT_SECRET_KEY=your-generated-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Note: NEXT_PUBLIC_API_URL is for frontend, not backend
```

### Step 3: Create `frontend/.env.local`

```bash
cd frontend
# Create .env.local
```

Add this content:
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Quick Setup Commands

### Windows PowerShell:
```powershell
# Backend .env
cd backend
Copy-Item "..\.env sample" .env
# Then edit .env and add your API keys and generate JWT_SECRET_KEY

# Frontend .env.local
cd ..\frontend
@"
NEXT_PUBLIC_API_URL=http://localhost:8000
"@ | Out-File -FilePath .env.local -Encoding utf8
```

### Mac/Linux:
```bash
# Backend .env
cd backend
cp "../.env sample" .env
# Then edit .env and add your API keys and generate JWT_SECRET_KEY

# Frontend .env.local
cd ../frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

## Verify Your Setup

### Check Backend .env:
```bash
cd backend
# Make sure .env exists
dir .env  # Windows
ls .env   # Mac/Linux
```

### Check Frontend .env.local:
```bash
cd frontend
# Make sure .env.local exists
dir .env.local  # Windows
ls .env.local   # Mac/Linux
```

## Troubleshooting

### "Module not found" or "Config error"
- Make sure `.env` is in `backend/` directory, not root
- Make sure you're running commands from `backend/` directory

### "JWT decode error" or "Invalid token"
- Check that `JWT_SECRET_KEY` is set in `backend/.env`
- Make sure it's the same key used when tokens were created
- If you change the secret, all existing tokens become invalid (users need to re-login)

### "Database connection failed"
- Check `DATABASE_URL` in `backend/.env`
- Make sure Docker container is running: `docker ps`

### Frontend can't connect to backend
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Make sure backend is running on port 8000

## Security Best Practices

1. **Never commit `.env` files** - They're in `.gitignore` for a reason!
2. **Use different secrets for dev/prod** - Don't use production secrets in development
3. **Rotate secrets periodically** - Change `JWT_SECRET_KEY` every few months
4. **Keep API keys secret** - Don't share them or commit them to git
5. **Use environment-specific files:**
   - Development: `.env`
   - Production: Set environment variables on your hosting platform (Vercel, Railway, etc.)

## File Structure

```
fiesta/
├── .env sample          # Template (safe to commit)
├── backend/
│   └── .env            # Backend secrets (DO NOT COMMIT)
└── frontend/
    └── .env.local      # Frontend config (DO NOT COMMIT)
```

