# Quick Start Guide - AI Fiesta

This guide will help you get AI Fiesta up and running in minutes.

## Prerequisites Check

Before starting, make sure you have:
- ✅ Python 3.11+ installed
- ✅ Node.js 18+ installed  
- ✅ Docker installed and running
- ✅ At least one AI provider API key (OpenAI, Anthropic, or Gemini)

## Step-by-Step Setup

### 1. Start the Database (2 minutes)

Open a terminal and run:

```bash
cd backend
docker-compose up -d
```

Wait a few seconds, then verify it's running:
```bash
docker ps
```

You should see `fiesta-db` container running.

### 2. Set Up Backend (5 minutes)

**2a. Create virtual environment:**
```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows CMD:
.venv\Scripts\activate.bat

# Mac/Linux:
source .venv/bin/activate
```

**2b. Install dependencies:**
```bash
pip install -r requirements.txt
```

**2c. Create `.env` file:**
```bash
# In the backend/ directory, create .env file
# Copy from root .env sample or create new one
```

Edit `backend/.env` and add at minimum:
```ini
DATABASE_URL=postgresql+asyncpg://fiesta_user:fiesta_pass@localhost:5433/fiesta_db
JWT_SECRET_KEY=change-this-to-a-random-secret-key-in-production
OPENAI_API_KEY=your_key_here
# OR
GEMINI_API_KEY=your_key_here
# OR  
ANTHROPIC_API_KEY=your_key_here
```

**2d. Run database migrations:**
```bash
# Make sure you're in backend/ directory
alembic upgrade head
```

**2e. Start the backend:**
```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
✅ Database initialized
INFO:     Uvicorn running on http://127.0.0.1:8000
```

✅ **Backend is running!** Keep this terminal open.

### 3. Set Up Frontend (3 minutes)

Open a **new terminal** window:

**3a. Install dependencies:**
```bash
cd frontend
npm install
```

**3b. Create `.env.local` file:**
```bash
# In the frontend/ directory, create .env.local
```

Add this content:
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**3c. Start the frontend:**
```bash
npm run dev
```

You should see:
```
  ▲ Next.js 16.0.7
  - Local:        http://localhost:3000
```

✅ **Frontend is running!**

### 4. Create Your First Account

1. Open your browser and go to: **http://localhost:3000**
2. You'll be redirected to the login page
3. Click **"Sign up"** or go to: **http://localhost:3000/register**
4. Fill in:
   - Email: `your@email.com`
   - Username: `yourusername`
   - Password: `yourpassword` (min 6 characters)
5. Click **"Sign up"**

You'll be automatically logged in and redirected to the chat page!

### 5. Start Chatting!

1. **Select models**: Choose one or more AI models from the selector
2. **Type a message**: Enter your question in the input field
3. **Send**: Click the send button or press Enter
4. **Watch responses**: See AI responses stream in real-time!

## Common Issues & Solutions

### ❌ "Database connection failed"
**Solution:**
- Make sure Docker is running: `docker ps`
- Check if container is up: `docker-compose up -d` (in `backend/` directory)
- Verify port 5433 is not in use by another service

### ❌ "Module not found" errors
**Solution:**
- Make sure virtual environment is activated (you should see `(.venv)` in terminal)
- Reinstall: `pip install -r requirements.txt`

### ❌ "401 Unauthorized" or "Invalid token"
**Solution:**
- Make sure you're logged in
- Try logging out and logging back in
- Check that `JWT_SECRET_KEY` is set in backend `.env`

### ❌ "No API key" errors
**Solution:**
- Add at least one API key to `backend/.env`:
  - `OPENAI_API_KEY=...` OR
  - `GEMINI_API_KEY=...` OR
  - `ANTHROPIC_API_KEY=...`

### ❌ Frontend can't connect to backend
**Solution:**
- Verify backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local` is `http://localhost:8000`
- Check `CORS_ALLOW_ORIGINS` in backend `.env` includes `http://localhost:3000` or is `["*"]`

### ❌ "Alembic" command not found
**Solution:**
- Make sure you're in the `backend/` directory
- Make sure virtual environment is activated
- Try: `python -m alembic upgrade head`

## Next Steps

- **View API docs**: http://localhost:8000/docs
- **Admin dashboard**: http://localhost:3000/admin (after logging in)
- **Pricing page**: http://localhost:3000/pricing

## Stopping the Application

**Stop frontend:**
- Press `Ctrl+C` in the frontend terminal

**Stop backend:**
- Press `Ctrl+C` in the backend terminal

**Stop database:**
```bash
cd backend
docker-compose down
```

## Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Google Gemini**: https://makersuite.google.com/app/apikey
- **Grok (X.AI)**: https://x.ai/api (if available)
- **Perplexity**: https://www.perplexity.ai/settings/api

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- View API documentation at http://localhost:8000/docs
- Check backend logs for error messages
- Check browser console (F12) for frontend errors

