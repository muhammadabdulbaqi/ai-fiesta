# Fiesta — Full-Stack Multi-Provider AI Chat Platform

Fiesta is a modern, full-stack AI chat application that orchestrates multiple LLM providers (Gemini, OpenAI, Anthropic) with a unified streaming interface and a credit-based usage tracking system.

It consists of:

- **Backend:** FastAPI application with SSE streaming, provider abstraction, and subscription management.
- **Frontend:** Next.js (App Router) application with a responsive chat UI, real-time token tracking, and admin dashboard.

---

## Features

### Multi-Model Arena
Select multiple models (e.g., GPT-4 vs Gemini) and stream their responses side-by-side in real time.

### Multi-Provider Support
Seamlessly switch between Google Gemini, OpenAI (GPT-4/3.5), and Anthropic (Claude) models.

### Real-Time Streaming
Robust Server-Sent Events (SSE) implementation for typewriter-style responses.

### Usage Tracking
Granular accounting of tokens and "credits" per request.

### Subscription Simulation
In-memory tier system (Free, Pro, Enterprise) enforcing:
- Rate limits
- Model access
- Credit limits

### Admin Dashboard
View system-wide usage, provider costs, and manage user credits.

### Modern UI
Built with Next.js, Tailwind CSS, and Shadcn/UI.

---

## Tech Stack

### Backend (/app)
- FastAPI
- Python 3.11+
- Server-Sent Events (SSE)
- In-memory database (migration to PostgreSQL planned)

### Frontend (/)
- Next.js 15+ (App Router)
- Tailwind CSS
- Shadcn/UI
- Custom SSE hooks

---

## Quick Start (Local Development)

You need Python 3.11+ and Node.js 18+ installed.

### 1. Backend Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
./.venv/Scripts/Activate.ps1   # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

Create .env:

```ini
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
CORS_ALLOW_ORIGINS=["http://localhost:3000"]
```

Run the backend:

```bash
uvicorn main:app --reload --port 8000
```

---

### 2. Frontend Setup

Install dependencies:

```bash
npm install
```

Create .env.local:

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEFAULT_USER_ID=demo-user-1
```

Run:

```bash
npm run dev
```

---

## Project Structure

```
fiesta/
├── app/
│   ├── routers/
│   ├── llm/
│   ├── models.py
│   └── main.py
├── components/
├── hooks/
├── lib/
├── public/
├── README.md
├── requirements.txt
└── package.json
```

---

## Testing

### Backend-only streaming test:

1. Start backend
2. Open: http://localhost:8000/test_client.html

### Provider verification

```bash
python testing/test_providers.py --check-keys
python testing/test_gemini.py
```

---

## Roadmap & Status

### Phase 1: Foundation (Completed)
- FastAPI SSE streaming
- Provider abstraction
- Basic frontend
- Credit/token deduction logic

### Phase 2: Stability & Experience (In Progress)
- Streaming bug fixes
- Multi-model toggle
- Conversation history UI
- Advanced usage tracking

### Phase 3: Production Hardening (Next)
- PostgreSQL migration
- Real authentication (NextAuth/Clerk)
- LangGraph agent integration

---

## Troubleshooting

### CORS Errors
Ensure .env CORS origins match: http://localhost:3000

### Streaming Issues
Backend may be missing `google-generativeai`; if so, Mock provider is used.

### 429 Quota Exceeded
Common with free-tier keys; backend sends an SSE error event.
