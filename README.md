# Fiesta — FastAPI LLM Backend (Working Draft)

This README documents the current state of the project and a concise roadmap in Markdown (next steps). It is intended as a single-source-of-truth for the team to run the app locally, understand architectural decisions, and follow the planned work.

---

## Current system (what we have so far)

- Framework: FastAPI application (`main.py`) with async endpoints and SSE streaming support.
- Providers implemented (pluggable): OpenAI, Anthropic, Google Gemini (optional SDK). A `Mock` provider exists for local testing.
- Streaming: `POST /stream/chat` serves SSE (`text/event-stream`). The server attempts to use a provider's streaming API, but now gracefully falls back to non-streaming `generate()` plus emulated chunking when streaming is unavailable.
- Subscription/usage model: in-memory subscriptions with tiers (`app/models.py`). We migrated from a 1:1 token deduction to a credits-based model:
	- `MODEL_CREDIT_COSTS` maps models to credit multipliers.
	- `check_credits_available()` and `deduct_credits()` live in `app/dependencies.py`.
	- Responses include both token fields and credits fields for backward compatibility.
- Admin and user endpoints: provide subscription inspection, adding tokens/credits, and usage/cost reporting.
- Test client: a simple `test_client.html` in the project root that exercises the SSE streaming endpoint.
- Emulation: when streaming is not available, we emulate progressive delivery using `app/utils/stream_emulation.py`.

Key files (high-level):

- `main.py` — FastAPI app entrypoint and demo user bootstrap
- `app/config.py` — application settings
- `app/models.py` — in-memory data, subscription tiers, `MODEL_CREDIT_COSTS`
- `app/dependencies.py` — helpers for subscriptions, credits, tracking
- `app/routers/chat.py` — `/chat` and `/stream/chat` endpoints with SSE fallback logic
- `app/llm/*` — provider implementations (OpenAI, Anthropic, Gemini, Mock)
- `test_client.html` — simple client for SSE testing
- `docs/` — design docs and streaming notes

---

## How to run locally (dev)

Prerequisites (recommended): Python 3.11+, pip, virtualenv

1. Create a virtual environment and install requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set provider API keys in your environment or `.env` file if you use one:

- `OPENAI_API_KEY` — OpenAI (optional)
- `ANTHROPIC_API_KEY` — Anthropic (optional)
- `GEMINI_API_KEY` — Google Gemini (optional)

If you don't set them, the app will use the `Mock` provider or raise a friendly error when trying to instantiate a provider that requires an SDK.

3. Start the dev server:

```powershell
uvicorn main:app --reload --port 8000
```

4. Open the test client in your browser:

- `http://localhost:8000/test_client.html`

Use `demo-user-1` as the default demo user.

5. Try endpoints:

- `POST /chat` — non-streaming chat
- `POST /stream/chat` — SSE streaming chat
- `GET /chat/models` — list available models from the factory
- `GET /subscriptions/{user_id}` — subscription info
- `POST /subscriptions/{user_id}/add-credits` — (admin) add credits

---

## Current Streaming Behavior (summary)

- The SSE handler first attempts `provider.stream_generate()`.
- If the provider raises a quota/rate-limit error, we return an SSE `error` event with that message (so it is visible to the client).
- For other stream errors (or if the stream is silent), the server:
	1. Calls `provider.generate()` (non-streaming)
	2. Emulates chunked delivery via `emulate_stream_text()` and yields SSE chunk events
	3. If emulation produced nothing (very short content), send the full response as a single `chunk` event so clients always get visible text
- After streaming completes, credits are deduced via `deduct_credits()` and cost/usage recorded.

---

## Endpoints (quick reference)

- POST /chat
	- Body: {prompt, model, conversation_id?, user_id, max_tokens?, temperature?}
	- Returns final response JSON (non-stream)

- POST /stream/chat
	- Body: same as `/chat`
	- Returns SSE events: `chunk`, `done`, `error`

- GET /chat/models
	- Returns available models from the factory

- GET /subscriptions/{user_id}
	- Returns subscription detail incl. credits and tokens

- POST /subscriptions/{user_id}/add-credits
	- Admin endpoint to add credits for a user

- PUT /subscriptions/{user_id}/use-credits
	- Admin/test endpoint to deduct arbitrary credits (useful for testing)

- Admin endpoints for usage/cost reporting in `app/routers/admin.py`

---

## What we implemented that matters

- Pluggable provider architecture
- SSE streaming with robust fallback to non-streaming + emulation
- Credits-based accounting (per-model multipliers) to avoid 1:1 token → subscription losses
- Provider guards so missing SDKs don't crash import-time
- Clear SSE `error` events for quota/rate-limit issues

---

## Roadmap / Next steps (planning only)

Below is the prioritized plan, tasks and acceptance criteria in Markdown.

### 1) Frontend SPA (priority: high)

Goal: A developer-friendly SPA that exposes all user-facing features and admin dashboards.

Scope & features:

- Chat UI
	- Text input, model selector, streaming output pane (SSE), conversation list
	- Display tokens_used / credits_used and remaining balances in the UI
- Model management
	- Toggle models/providers on/off (server API toggles)
	- Show model status (enabled/disabled, streaming-supported or not)
- Multi-provider mode
	- If multiple models are enabled, allow running them sequentially or in parallel and present combined outputs (for now sequential is fine)
- Usage & cost dashboard
	- For an authenticated admin, display per-user real API usage and cost (provider/model breakdown)
	- Allow exporting CSV and filtering by provider/model/date
- Dev-run instructions
	- Use React + Vite (recommended) for local development, simple Node script to run dev server

Endpoints required on backend (implement if not present):

- `GET /admin/models` — list all models and their enabled/disabled state
- `POST /admin/models/{model}/toggle` — enable/disable a model for the system
- `GET /admin/usage/{user_id}` — detailed usage and cost (already present in `admin.py`)
- `GET /models/streamability` — quick probe to say whether the model supports streaming for this API key

Acceptance criteria:

- Developer can run the SPA locally and connect to local FastAPI (CORS preconfigured)
- Chat UI shows streaming output via SSE and falls back to non-streaming without manual config changes
- Admin can see cost/usage and toggle models

Notes about providers and local testing:

- Cloud providers (OpenAI, Anthropic, Gemini): require API keys and billing. No universal free unlimited plan — they provide limited free credits or tiers.
- For local testing without provider API keys:
	- `Mock` provider is available and works offline.
	- Alternatively, connect to local open-source LLMs (e.g., Llama.cpp/ggml, local Docker images) and expose a small adapter provider.
	- Hugging Face Inference API offers a free tier with rate limits and can be used as a provider if you want a cloud-backed free-ish provider.

Estimated tasks & timeline (rough):

- Scaffold React/Vite app + basic chat page — 1 day
- SSE integration + model selector + credits display — 0.5 day
- Admin dashboard + model toggles — 1 day
- Polish + export/CSV — 0.5–1 day

### 2) PostgreSQL + SQLModel (priority: medium-high)

Goal: Replace in-memory stores with durable Postgres-backed models and implement atomic credits deduction.

Scope & acceptance criteria:

- Add `SQLModel` (or SQLAlchemy) models for users, subscriptions, messages, cost_tracker, api_usage
- Implement migrations (Alembic)
- Implement credits deduction inside an atomic DB transaction using `SELECT ... FOR UPDATE` to avoid double-spend when concurrent requests occur
- Provide a simple migration script and Docker-compose snippet to run Postgres locally for development

Estimated tasks:

- Schema design & SQLModel classes: 0.5–1 day
- Alembic setup and initial migration: 0.5 day
- Replace in-memory reads/writes with DB session usage and add locking for deductions: 1–2 days

### 3) LangGraph integration (priority: medium)

Goal: Add LangGraph to enable richer history graphs and attach reasoning/agent flows.

Scope & acceptance criteria:

- Add a LangGraph client integration in backend to mirror conversation events to LangGraph
- Store a pointer in messages to LangGraph nodes when needed
- Provide a small UI to visualize history via LangGraph (optional)

Notes: LangGraph can enrich message graphs and manage higher-level orchestration. We'll design minimal integration first and expand later.

Estimated tasks: 1–3 days depending on depth of integration.

### 4) Tests & CI (priority: medium)

Goal: Add unit/integration tests for credit deductions, SSE fallback, provider factory and admin endpoints and wire up CI (GitHub Actions).

Acceptance criteria:

- Unit tests for `deduct_credits()`, `check_credits_available()`, and SSE fallback logic
- Integration test: simulate a provider that raises stream exceptions and verify the SSE client receives chunk events via emulation
- GitHub Actions workflow that runs tests and linters on PRs

Estimated tasks: 1–2 days.

---

## Immediate next action 

1. Scaffold the frontend (React + Vite) and wire the basic Chat UI to existing endpoints (`/stream/chat`, `/chat`, `/chat/models`).
2. Add admin endpoints for model toggling and model streamability checks. Integrate these into the frontend.

If you want, I can start by scaffolding the frontend and adding the new admin endpoints; say "Start frontend scaffolding" and I'll:

- create a `web/` folder with a Vite + React starter,
- add a simple Chat page that uses SSE and shows credits/tokens,
- implement an `/admin/models` and `/admin/models/{model}/toggle` endpoint in the backend, and
- wire the frontend toggles to those endpoints.

---






================================================
FILE: api_test_results.json
================================================
{
  "timestamp": "2025-12-05T08:51:10.949031",
  "api_tokens_valid": {
    "gemini": true,
    "openai": true,
    "anthropic": true
  },
  "models_by_provider": {
    "gemini": [
      "gemini-2.5-flash",
      "gemini-2.5-pro",
      "gemini-2.0-flash-exp",
      "gemini-2.0-flash",
      "gemini-2.0-flash-001",
      "gemini-2.0-flash-lite-001",
      "gemini-2.0-flash-lite",
      "gemini-2.0-flash-lite-preview-02-05",
      "gemini-2.0-flash-lite-preview",
      "gemini-2.0-pro-exp",
      "gemini-2.0-pro-exp-02-05",
      "gemini-exp-1206",
      "gemini-2.5-flash-preview-tts",
      "gemini-2.5-pro-preview-tts",
      "gemma-3-1b-it",
      "gemma-3-4b-it",
      "gemma-3-12b-it",
      "gemma-3-27b-it",
      "gemma-3n-e4b-it",
      "gemma-3n-e2b-it",
      "gemini-flash-latest",
      "gemini-flash-lite-latest",
      "gemini-pro-latest",
      "gemini-2.5-flash-lite",
      "gemini-2.5-flash-image-preview",
      "gemini-2.5-flash-image",
      "gemini-2.5-flash-preview-09-2025",
      "gemini-2.5-flash-lite-preview-09-2025",
      "gemini-3-pro-preview",
      "gemini-3-pro-image-preview",
      "nano-banana-pro-preview",
      "gemini-robotics-er-1.5-preview",
      "gemini-2.5-computer-use-preview-10-2025"
    ],
    "openai": [
      "gpt-4-0613",
      "gpt-4",
      "gpt-3.5-turbo",
      "gpt-5.1-codex-max",
      "gpt-5.1-2025-11-13",
      "gpt-5.1",
      "gpt-5.1-codex",
      "gpt-5.1-codex-mini",
      "gpt-3.5-turbo-instruct",
      "gpt-3.5-turbo-instruct-0914",
      "gpt-4-1106-preview",
      "gpt-3.5-turbo-1106",
      "gpt-4-0125-preview",
      "gpt-4-turbo-preview",
      "gpt-3.5-turbo-0125",
      "gpt-4-turbo",
      "gpt-4-turbo-2024-04-09",
      "gpt-4o",
      "gpt-4o-2024-05-13",
      "gpt-4o-mini-2024-07-18",
      "gpt-4o-mini",
      "gpt-4o-2024-08-06",
      "chatgpt-4o-latest",
      "gpt-4o-audio-preview",
      "gpt-4o-realtime-preview",
      "gpt-4o-realtime-preview-2024-12-17",
      "gpt-4o-audio-preview-2024-12-17",
      "gpt-4o-mini-realtime-preview-2024-12-17",
      "gpt-4o-mini-audio-preview-2024-12-17",
      "gpt-4o-mini-realtime-preview",
      "gpt-4o-mini-audio-preview",
      "gpt-4o-2024-11-20",
      "gpt-4o-search-preview-2025-03-11",
      "gpt-4o-search-preview",
      "gpt-4o-mini-search-preview-2025-03-11",
      "gpt-4o-mini-search-preview",
      "gpt-4o-transcribe",
      "gpt-4o-mini-transcribe",
      "gpt-4o-mini-tts",
      "gpt-4.1-2025-04-14",
      "gpt-4.1",
      "gpt-4.1-mini-2025-04-14",
      "gpt-4.1-mini",
      "gpt-4.1-nano-2025-04-14",
      "gpt-4.1-nano",
      "gpt-image-1",
      "gpt-4o-realtime-preview-2025-06-03",
      "gpt-4o-audio-preview-2025-06-03",
      "gpt-4o-transcribe-diarize",
      "gpt-5-chat-latest",
      "gpt-5-2025-08-07",
      "gpt-5",
      "gpt-5-mini-2025-08-07",
      "gpt-5-mini",
      "gpt-5-nano-2025-08-07",
      "gpt-5-nano",
      "gpt-audio-2025-08-28",
      "gpt-realtime",
      "gpt-realtime-2025-08-28",
      "gpt-audio",
      "gpt-5-codex",
      "gpt-image-1-mini",
      "gpt-5-pro-2025-10-06",
      "gpt-5-pro",
      "gpt-audio-mini",
      "gpt-audio-mini-2025-10-06",
      "gpt-5-search-api",
      "gpt-realtime-mini",
      "gpt-realtime-mini-2025-10-06",
      "gpt-5-search-api-2025-10-14",
      "gpt-5.1-chat-latest",
      "gpt-3.5-turbo-16k"
    ],
    "anthropic": [
      "claude-3-opus-20240229",
      "claude-3-sonnet-20240229",
      "claude-3-haiku-20240307"
    ]
  },
  "usage_summary": {
    "total_calls": 3,
    "total_tokens": 59,
    "total_cost_usd": 3.4e-05,
    "by_provider": {
      "gemini": {
        "calls": 1,
        "tokens": 11,
        "cost": 3.5e-06,
        "errors": 0
      },
      "openai": {
        "calls": 1,
        "tokens": 20,
        "cost": 1.4e-05,
        "errors": 0
      },
      "anthropic": {
        "calls": 1,
        "tokens": 28,
        "cost": 1.6e-05,
        "errors": 0
      }
    }
  },
  "test_results": {
    "gemini": "OK",
    "openai": "OK",
    "anthropic": "OK"
  }
}


================================================
FILE: components.json
================================================
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}




================================================
FILE: main.py
================================================
"""Application entrypoint. Minimal app that composes routers and settings."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import FileResponse

from app.config import settings
from app.routers import users as users_router
from app.routers import subscriptions as subscriptions_router
from app.routers import chat as chat_router
from app.routers import admin as admin_router
from app import models

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router.router)
app.include_router(subscriptions_router.router)
app.include_router(chat_router.router)
app.include_router(admin_router.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": settings.app_name,
        "version": settings.version,
        "docs": settings.docs_url,
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    from datetime import datetime

    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": settings.version,
    }


@app.get("/test_client.html", include_in_schema=False)
async def serve_test_client():
    """Serve the local HTML test client for WebSocket streaming tests."""
    client_path = os.path.join(os.getcwd(), "test_client.html")
    if not os.path.exists(client_path):
        return {"error": "test_client.html not found in project root"}
    return FileResponse(client_path, media_type="text/html")


@app.on_event("startup")
async def startup_event():
    # Create demo user and subscription (kept for backwards compatibility)
    import uuid
    from datetime import datetime
    # Create a deterministic demo user for local testing so the test client
    # can use a stable `user_id` like `demo-user-1`.
    demo_user_id = "demo-user-1"
    demo_user = {
        "id": demo_user_id,
        "email": settings.demo_user_email,
        "username": settings.demo_user_username,
        "hashed_password": f"hashed_{settings.demo_user_password}",
        "is_active": True,
        "created_at": datetime.now(),
    }

    # Only add if not present (avoid overwriting existing demo user)
    if demo_user_id not in models.users_db:
        models.users_db[demo_user_id] = demo_user

    # Give the demo user a free subscription (flash Gemini is allowed on free)
    demo_subscription = models.create_default_subscription(demo_user_id, "free")
    demo_subscription["tokens_used"] = 0
    demo_subscription["tokens_remaining"] = demo_subscription["tokens_limit"]
    demo_subscription["credits_used"] = 0
    demo_subscription["credits_remaining"] = demo_subscription.get("credits_limit", demo_subscription.get("tokens_limit"))

    print(f"✅ Demo user ready: {demo_user['email']} (ID: {demo_user_id})")



================================================
FILE: next.config.mjs
================================================
/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig




================================================
FILE: next_stage.md
================================================
# AI Fiesta Frontend Development Roadmap

## 🚨 Phase 1: Fix Critical Streaming Bug (HIGH PRIORITY)

### Problem Analysis
**Symptom:** Text is duplicating and splitting mid-word during SSE streaming
```
"The fastest human inThe fastest human in the world is the world is Usain Bolt Usain Bolt..."
```

**Likely Causes:**
1. **Double event emission** - Same chunk being sent twice from backend
2. **Buffer flushing issue** - SSE chunks not properly delimited
3. **React state race condition** - Multiple setState calls overlapping
4. **Chunk boundary splitting** - Words split across SSE message boundaries

### Debug Steps

#### Step 1: Test with `test_client.html` (Isolate backend)
- Open `http://localhost:8000/test_client.html`
- Send same prompt and observe raw SSE chunks
- Check browser DevTools Network tab → EventStream
- **If duplicates appear here:** Backend issue
- **If clean here:** Frontend React issue

#### Step 2: Backend Investigation (`app/routers/chat.py`)
**File:** `app/routers/chat.py` line 200-300 (stream_chat endpoint)

Check for:
```python
# Look for double yield
async for chunk in provider.stream_generate(...):
    # Is this yielding twice?
    payload = json.dumps({"type": "chunk", "content": chunk_text})
    yield f"data: {payload}\n\n"  # ← Check if called twice
```

**Potential fixes:**
- Add logging: `print(f"Yielding chunk: {chunk_text}")`
- Ensure no duplicate async iteration
- Check `emulate_stream_text()` in `app/utils/stream_emulation.py`

#### Step 3: Frontend Investigation (`hooks/use-chat-sse.ts`)
**File:** `hooks/use-chat-sse.ts` line 50-100

Check for:
```typescript
// State update race condition
setMessages((prev) => {
  const updated = [...prev]
  updated[updated.length - 1].content += data.content || ""  // ← Concatenating twice?
  return updated
})
```

**Potential fixes:**
- Add console.log before setState
- Use functional update pattern (already doing this ✓)
- Check if multiple SSE listeners registered

#### Step 4: SSE Parser Issue
**File:** `hooks/use-chat-sse.ts` line 70-90

```typescript
// Buffer handling
buffer += decoder.decode(value, { stream: true })
const events = buffer.split("\n\n")
buffer = events.pop() || ""
```

**Check:**
- Are events being parsed multiple times?
- Is `buffer` accumulating old data?

### Action Items
- [ ] Test in `test_client.html` first
- [ ] Add logging to backend `stream_chat()` 
- [ ] Add console.log to frontend `use-chat-sse.ts`
- [ ] Compare raw SSE events vs rendered UI
- [ ] Test with different models (Gemini, OpenAI, Anthropic)

---

## 🎯 Phase 2: Multi-Model Toggle Feature (MEDIUM PRIORITY)

### Goal
Enable users to select multiple models and stream responses simultaneously.

### UI Design
```
┌─────────────────────────────────────────────────────┐
│ 🎉 AI Fiesta                          Tokens: 500   │
│                                                      │
│ Active Models:                                       │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ GPT-4     ⚫ │ │ Gemini    ⚫ │ │ Claude    ⚪ │ │
│ │ OpenAI       │ │ Google       │ │ Anthropic    │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Implementation Plan

#### Step 1: Create Toggle Component
**New file:** `components/model-toggle.tsx`

```typescript
interface ModelToggleProps {
  availableModels: Model[]
  enabledModels: string[]
  onToggle: (modelId: string) => void
  userTier: string
}

export function ModelToggle({ availableModels, enabledModels, onToggle, userTier }) {
  // Filter models by user tier
  // Display as chips with toggle switches
  // Show provider logo/icon
}
```

#### Step 2: Update Chat Page State
**File:** `app/page.tsx`

```typescript
// Replace single model state
const [selectedModel, setSelectedModel] = useState("")

// With multi-model state
const [enabledModels, setEnabledModels] = useState<string[]>(["gemini-2.5-flash"])

const toggleModel = (modelId: string) => {
  setEnabledModels(prev => 
    prev.includes(modelId) 
      ? prev.filter(m => m !== modelId)
      : [...prev, modelId]
  )
}
```

#### Step 3: Backend Multi-Model Endpoint
**File:** `app/routers/chat.py`

**Option A:** Send parallel requests from frontend
```typescript
// Frontend handles multiple SSE connections
enabledModels.forEach(model => {
  sendMessage(prompt, model, ...)
})
```

**Option B:** Create backend endpoint (RECOMMENDED)
```python
@router.post("/stream/chat/multi")
async def stream_chat_multi(request: Request):
    """
    Accept multiple models and stream all responses.
    
    Response format:
    data: {"type": "chunk", "model": "gpt-4", "content": "..."}
    data: {"type": "chunk", "model": "gemini-2.5-flash", "content": "..."}
    data: {"type": "done", "model": "gpt-4", "tokens_used": 100}
    """
    # Implementation: asyncio.gather() to stream multiple models
```

#### Step 4: UI Layout for Multiple Responses
**File:** `components/multi-model-response.tsx`

**Layout Options:**

**Option A: Side-by-side columns**
```
┌─────────────────┬─────────────────┬─────────────────┐
│ GPT-4           │ Gemini          │ Claude          │
├─────────────────┼─────────────────┼─────────────────┤
│ Response text   │ Response text   │ Response text   │
│ streaming...    │ streaming...    │ streaming...    │
└─────────────────┴─────────────────┴─────────────────┘
```

**Option B: Stacked cards** (RECOMMENDED - better for mobile)
```
┌───────────────────────────────────────┐
│ 🤖 GPT-4                              │
│ Response text streaming...            │
└───────────────────────────────────────┘

┌───────────────────────────────────────┐
│ ✨ Gemini                             │
│ Response text streaming...            │
└───────────────────────────────────────┘
```

#### Step 5: Token/Credit Tracking
- Track usage per model
- Show individual model costs
- Deduct credits for each model separately

### Action Items
- [ ] Create `components/model-toggle.tsx`
- [ ] Update `app/page.tsx` with multi-model state
- [ ] Create `POST /stream/chat/multi` endpoint
- [ ] Create `components/multi-model-response.tsx`
- [ ] Update `hooks/use-chat-sse.ts` for multi-model
- [ ] Add per-model cost tracking

---

## 🧹 Phase 3: Clean Up UI / Add Missing APIs (LOW PRIORITY)

### Option A: Remove Unimplemented Features

**File:** `components/sidebar.tsx`

Remove or comment out:
```typescript
// Remove these until APIs exist:
- Avatars button (line 40)
- Projects button (line 47)
- Games button (line 54)
- Yesterday history (line 65)
```

**Keep only:**
- New Chat
- Admin link
- Settings (configure later)

### Option B: Implement Conversation APIs

#### Backend APIs Needed

**File:** `app/routers/chat.py`

```python
@router.post("/conversations/")
async def create_conversation(user_id: str):
    """Create new conversation"""
    pass

@router.get("/conversations/{user_id}")
async def list_conversations(user_id: str):
    """List user's conversations"""
    pass

@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str):
    """Get messages in conversation"""
    pass

@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete conversation"""
    pass
```

#### Frontend Updates

**File:** `components/sidebar.tsx`

```typescript
const [conversations, setConversations] = useState([])

useEffect(() => {
  // Fetch user's conversations
  fetch(`/conversations/${userId}`)
    .then(res => res.json())
    .then(setConversations)
}, [])

// Display in "Yesterday" section
{conversations.map(conv => (
  <button onClick={() => loadConversation(conv.id)}>
    {conv.title || conv.first_message}
  </button>
))}
```

### Recommendation
**Go with Option A** - Remove features for now. Add conversation APIs in Phase 4 after multi-model works.

---

## 📋 Summary Timeline

### Week 1
- [ ] **Day 1-2:** Fix streaming duplication bug
- [ ] **Day 3-4:** Test across all providers (Gemini, OpenAI, Anthropic)

### Week 2
- [ ] **Day 1-2:** Create model toggle component
- [ ] **Day 3-4:** Implement multi-model streaming backend
- [ ] **Day 5:** Multi-model UI layout

### Week 3
- [ ] **Day 1-2:** Clean up sidebar (remove unimplemented features)
- [ ] **Day 3:** Polish and testing
- [ ] **Day 4-5:** Buffer for bug fixes

---

## 🎯 Next Immediate Action

**START HERE:** Fix the streaming bug first before building new features.

1. Open `test_client.html`
2. Send a test prompt
3. Open browser DevTools → Network → EventStream
4. Look for duplicate chunks
5. Report back findings

Once streaming is stable, we build multi-model toggle.


================================================
FILE: package.json
================================================
{
  "name": "fiesta",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "next build",
    "dev": "next dev",
    "lint": "eslint .",
    "start": "next start"
  },
  "dependencies": {
    "@hookform/resolvers": "^3.10.0",
    "@radix-ui/react-accordion": "1.2.2",
    "@radix-ui/react-alert-dialog": "1.1.4",
    "@radix-ui/react-aspect-ratio": "1.1.1",
    "@radix-ui/react-avatar": "1.1.2",
    "@radix-ui/react-checkbox": "1.1.3",
    "@radix-ui/react-collapsible": "1.1.2",
    "@radix-ui/react-context-menu": "2.2.4",
    "@radix-ui/react-dialog": "1.1.4",
    "@radix-ui/react-dropdown-menu": "2.1.4",
    "@radix-ui/react-hover-card": "1.1.4",
    "@radix-ui/react-label": "2.1.1",
    "@radix-ui/react-menubar": "1.1.4",
    "@radix-ui/react-navigation-menu": "1.2.3",
    "@radix-ui/react-popover": "1.1.4",
    "@radix-ui/react-progress": "1.1.1",
    "@radix-ui/react-radio-group": "1.2.2",
    "@radix-ui/react-scroll-area": "1.2.2",
    "@radix-ui/react-select": "2.1.4",
    "@radix-ui/react-separator": "1.1.1",
    "@radix-ui/react-slider": "1.2.2",
    "@radix-ui/react-slot": "1.1.1",
    "@radix-ui/react-switch": "1.1.2",
    "@radix-ui/react-tabs": "1.1.2",
    "@radix-ui/react-toast": "1.2.4",
    "@radix-ui/react-toggle": "1.1.1",
    "@radix-ui/react-toggle-group": "1.1.1",
    "@radix-ui/react-tooltip": "1.1.6",
    "@vercel/analytics": "latest",
    "autoprefixer": "^10.4.20",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "cmdk": "1.0.4",
    "date-fns": "4.1.0",
    "embla-carousel-react": "8.5.1",
    "input-otp": "1.4.1",
    "lucide-react": "^0.454.0",
    "next": "16.0.7",
    "next-themes": "^0.4.6",
    "react": "19.2.0",
    "react-day-picker": "9.8.0",
    "react-dom": "19.2.0",
    "react-hook-form": "^7.60.0",
    "react-resizable-panels": "^2.1.7",
    "recharts": "2.15.4",
    "sonner": "^1.7.4",
    "tailwind-merge": "^2.5.5",
    "tailwindcss-animate": "^1.0.7",
    "vaul": "^1.1.2",
    "zod": "3.25.76"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.1.9",
    "@types/node": "^22",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "postcss": "^8.5",
    "tailwindcss": "^4.1.9",
    "tw-animate-css": "1.3.3",
    "typescript": "^5"
  }
}




================================================
FILE: postcss.config.mjs
================================================
/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}

export default config




================================================
FILE: README-FRONTEND.md
================================================
# AI Fiesta Frontend

Next.js frontend application for the AI Fiesta FastAPI backend.

## Setup

1. Install dependencies:
```bash
npm install
# or
pnpm install
# or
yarn install
```

2. Create `.env.local` file (or copy from `.env.local.example`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEFAULT_USER_ID=demo-user-1
```

3. Make sure the FastAPI backend is running on port 8000 (or update the URL in `.env.local`)

4. Start the development server:
```bash
npm run dev
# or
pnpm dev
# or
yarn dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Features

- **Chat Interface**: Real-time streaming chat with multiple AI models
- **Model Selector**: Choose from available models based on your subscription tier
- **Usage Tracking**: View token and credit usage in real-time
- **Admin Dashboard**: Monitor system usage, costs, and user subscriptions
- **Responsive Design**: Works on desktop and mobile devices

## Project Structure

- `app/` - Next.js app directory with pages and layout
- `components/` - React components
  - `ui/` - shadcn/ui component library
- `hooks/` - Custom React hooks
- `lib/` - Utilities and API client

## API Integration

The frontend connects to the FastAPI backend at the URL specified in `NEXT_PUBLIC_API_URL`. 

The API client (`lib/api.ts`) handles:
- Token usage tracking
- Subscription management
- Model listing
- Admin statistics

SSE streaming is handled by the `useChatSSE` hook (`hooks/use-chat-sse.ts`).

## CORS Configuration

Make sure your FastAPI backend has CORS configured to allow requests from `http://localhost:3000` (or your frontend URL). The backend should already have CORS middleware set up in `main.py`.




================================================
FILE: requirements.txt
================================================
# FastAPI LLM Backend - Phase 1 Requirements
# Basic FastAPI setup with no database or external services

fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic[email]==2.5.0
python-multipart==0.0.6

# Development tools (optional)
# pytest==7.4.3
# httpx==0.25.2  # For testing

# LLM provider libraries (optional)
openai==1.12.0
anthropic==0.18.1
google-generativeai==0.3.2
tiktoken==0.5.2
httpx==0.26.0


================================================
FILE: SETUP.md
================================================
# Quick Setup Guide

## Frontend Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   Create a `.env.local` file in the project root:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_DEFAULT_USER_ID=demo-user-1
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Backend Setup

Make sure your FastAPI backend is running:

1. **Activate virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Start the server:**
   ```powershell
   uvicorn main:app --reload --port 8000
   ```

3. **Verify CORS:**
   The backend should already have CORS configured to allow all origins (`*`). If you need to restrict it, update `app/config.py` or set `CORS_ALLOW_ORIGINS` environment variable.

## Testing

1. Start both servers (FastAPI on port 8000, Next.js on port 3000)
2. Open http://localhost:3000
3. Try sending a message in the chat interface
4. Check the admin dashboard at http://localhost:3000/admin

## Troubleshooting

- **CORS errors**: Make sure `CORS_ALLOW_ORIGINS` in backend includes `http://localhost:3000` or is set to `["*"]`
- **API connection errors**: Verify `NEXT_PUBLIC_API_URL` in `.env.local` matches your backend URL
- **Module not found**: Run `npm install` to ensure all dependencies are installed




================================================
FILE: test_client.html
================================================
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Fiesta WebSocket Streaming Test</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; }
        #chat { border: 1px solid #ddd; padding: 16px; height: 420px; overflow-y: auto; background: #f9f9f9 }
        .message { margin: 8px 0; padding: 8px 10px; border-radius: 6px; }
        .user { background: #e3f2fd; text-align: right; }
        .assistant { background: #fff; }
        .info { color: #666; font-size: 13px; margin-top: 8px }
        #controls { margin-top: 12px }
        input[type=text] { width: 70%; padding: 8px }
        button { padding: 8px 12px }
    </style>
</head>
<body>
    <h1>Fiesta HTTP-SSE Streaming Test</h1>
    <div>
        <label>User ID: <input id="userId" type="text" value="demo-user-1" /></label>
        <label style="margin-left:16px">Model:
            <select id="model">
                <optgroup label="Gemini">
                    <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                    <option value="gemini-2.5-pro" selected>gemini-2.5-pro</option>
                </optgroup>
                <optgroup label="OpenAI">
                    <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                    <option value="gpt-4">gpt-4</option>
                </optgroup>
                <optgroup label="Anthropic">
                    <option value="claude-3-haiku-20240307">claude-3-haiku-20240307</option>
                    <option value="claude-3-opus-20240229">claude-3-opus-20240229</option>
                </optgroup>
            </select>
        </label>
    </div>

    <div id="chat"></div>

    <div id="controls">
        <input id="prompt" type="text" placeholder="Type a prompt... (e.g. Write a short haiku about coding)" />
        <button id="send">Send (HTTP-SSE)</button>
        <div id="status" class="info">Idle</div>
    </div>

    <script>
        const chatDiv = document.getElementById('chat');
        const promptInput = document.getElementById('prompt');
        const sendButton = document.getElementById('send');
        const statusDiv = document.getElementById('status');
        const userIdInput = document.getElementById('userId');
        const modelSelect = document.getElementById('model');

        function addMessage(text, cls) {
            const el = document.createElement('div');
            el.className = 'message ' + cls;
            el.textContent = text;
            chatDiv.appendChild(el);
            chatDiv.scrollTop = chatDiv.scrollHeight;
            return el;
        }

        async function sendMessage() {
            const prompt = promptInput.value.trim();
            if (!prompt) return;
            addMessage(prompt, 'user');
            statusDiv.textContent = 'Streaming...';

            const payload = {
                prompt: prompt,
                model: modelSelect.value,
                user_id: userIdInput.value,
                max_tokens: 400
            };

            try {
                const res = await fetch('/stream/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    addMessage('Server returned ' + res.status, 'assistant');
                    statusDiv.textContent = 'Idle';
                    return;
                }

                const reader = res.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';
                let currentMessage = null;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    let parts = buffer.split('\n\n');
                    buffer = parts.pop();
                    for (const part of parts) {
                        if (!part.trim()) continue;
                        // each part is like: data: {json}
                        const lines = part.split('\n').map(l => l.trim());
                        for (const line of lines) {
                            if (line.startsWith('data:')) {
                                const jsonText = line.slice(5).trim();
                                try {
                                    const obj = JSON.parse(jsonText);
                                    if (obj.type === 'chunk') {
                                        if (!currentMessage) {
                                            currentMessage = document.createElement('div');
                                            currentMessage.className = 'message assistant';
                                            chatDiv.appendChild(currentMessage);
                                        }
                                        currentMessage.textContent += obj.content;
                                        chatDiv.scrollTop = chatDiv.scrollHeight;
                                    } else if (obj.type === 'done') {
                                        const info = document.createElement('div');
                                        info.className = 'info';
                                        let text = `Used ${obj.tokens_used} tokens. ${obj.tokens_remaining} remaining. Model: ${obj.model}`;
                                        if (obj.credits_used !== undefined) {
                                            text += ` | Credits used: ${obj.credits_used}. Credits remaining: ${obj.credits_remaining}`;
                                        }
                                        info.textContent = text;
                                        chatDiv.appendChild(info);
                                        currentMessage = null;
                                    } else if (obj.type === 'error') {
                                        addMessage('Error: ' + (obj.message || obj.error), 'assistant');
                                        currentMessage = null;
                                    }
                                } catch (e) {
                                    console.error('Invalid JSON in SSE', e, jsonText);
                                }
                            }
                        }
                    }
                }

                // flush remaining buffer (if any)
                statusDiv.textContent = 'Idle';
                promptInput.value = '';
            } catch (e) {
                console.error(e);
                addMessage('Streaming failed: ' + String(e), 'assistant');
                statusDiv.textContent = 'Idle';
            }
        }

        sendButton.onclick = sendMessage;
        promptInput.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
    </script>
</body>
</html>


================================================
FILE: test_gemini.py
================================================
"""
Quick test to verify Gemini models work
Run this to see which models are actually available
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Please install: pip install google-generativeai")
    exit(1)

async def test_gemini_models():
    """Test which Gemini models actually work"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        return
    
    genai.configure(api_key=api_key)
    
    # Models to test (from most likely to work, to least likely)
    models_to_test = [
        "gemini-2.5-flash",      # Most likely to work
        "gemini-2.5-pro",        # Should work
        "gemini-pro",            # Older, stable
        "gemini-2.5-flash-8b",   # Newer, efficient
        "gemini-2.0-flash-exp",  # Experimental (might not be available)
    ]
    
    print("Testing Gemini models...\n")
    print("=" * 60)
    
    working_models = []
    failed_models = []
    
    for model_name in models_to_test:
        print(f"\n Testing: {model_name}")
        print("-" * 60)
        
        try:
            model = genai.GenerativeModel(model_name)
            
            # Test non-streaming first
            print("   [1/2] Testing non-streaming generation...")
            response = await model.generate_content_async(
                "Say 'I work!' and nothing else.",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=50,
                    temperature=0.1
                )
            )
            
            # Extract text robustly from candidates -> content -> parts
            result_text = ""
            if hasattr(response, 'candidates'):
                for cand in response.candidates:
                    content = getattr(cand, 'content', None)
                    if content and getattr(content, 'parts', None):
                        for part in content.parts:
                            if getattr(part, 'text', None):
                                result_text += part.text
            print(f"   ✅ Non-streaming works: {result_text[:50]}")
            
            # Test streaming
            print("   [2/2] Testing streaming generation...")
            chunks = []
            stream = await model.generate_content_async(
                "Count to 3 slowly: 1",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=20,
                    temperature=0.1
                ),
                stream=True
            )
            
            async for chunk in stream:
                # Extract chunk text from candidates -> content -> parts
                if hasattr(chunk, 'candidates'):
                    for cand in chunk.candidates:
                        content = getattr(cand, 'content', None)
                        if content and getattr(content, 'parts', None):
                            for part in content.parts:
                                if getattr(part, 'text', None):
                                    chunks.append(part.text)
            
            print(f"   ✅ Streaming works: Received {len(chunks)} chunks")
            print(f"   ✅ {model_name} - WORKING!")
            working_models.append(model_name)
            
        except Exception as e:
            error_str = str(e)
            print(f"   ❌ FAILED: {error_str[:100]}")
            failed_models.append((model_name, error_str))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if working_models:
        print(f"\n✅ WORKING MODELS ({len(working_models)}):")
        for model in working_models:
            print(f"   - {model}")
        print(f"\n👉 USE THIS IN YOUR CODE:")
        print(f'   model = "{working_models[0]}"  # Recommended')
    else:
        print("\n❌ NO WORKING MODELS FOUND")
    
    if failed_models:
        print(f"\n❌ FAILED MODELS ({len(failed_models)}):")
        for model, error in failed_models:
            print(f"   - {model}")
            if "404" in error:
                print(f"     → Not available in your region/tier")
            elif "permission" in error.lower():
                print(f"     → API key lacks permissions")
    
    print("\n" + "=" * 60)
    
    # List all available models from API
    print("\nFetching available models from Gemini API...")
    try:
        available_models = genai.list_models()
        print("\nAll available models:")
        for model in available_models:
            if "generateContent" in model.supported_generation_methods:
                print(f"   ✅ {model.name}")
    except Exception as e:
        print(f"   ❌ Could not list models: {e}")
    
    print("\n")

if __name__ == "__main__":
    asyncio.run(test_gemini_models())


================================================
FILE: test_gemini_25.py
================================================
"""
Test Gemini 2.5 models with correct model names
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai

async def test_gemini_25():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        return
    
    genai.configure(api_key=api_key)
    
    # Test with actual model path (what the API expects)
    models_to_test = [
        ("gemini-2.5-flash", "models/gemini-2.5-flash"),
        ("gemini-2.5-pro", "models/gemini-2.5-pro"),
    ]
    
    print("Testing Gemini 2.5 models...\n")
    
    for friendly_name, actual_path in models_to_test:
        print(f"Testing: {friendly_name} (using {actual_path})")
        print("-" * 60)
        
        try:
            # Use the actual model path with "models/" prefix
            model = genai.GenerativeModel(actual_path)
            
            # Test non-streaming
            print("  [1/2] Non-streaming test...")
            response = await model.generate_content_async(
                "Say 'Hello from Gemini 2.5!' and nothing else.",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=50,
                    temperature=0.1
                )
            )
            print(f"  ✅ Response: {response.text}")
            
            # Test streaming
            print("  [2/2] Streaming test...")
            chunks = []
            stream = await model.generate_content_async(
                "Count: 1, 2, 3",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=20,
                    temperature=0.1
                ),
                stream=True
            )
            
            async for chunk in stream:
                if hasattr(chunk, 'text'):
                    chunks.append(chunk.text)
                    print(f"  📦 Chunk: {chunk.text}")
            
            print(f"  ✅ Total chunks: {len(chunks)}")
            print(f"  ✅ {friendly_name} WORKS!\n")
            
        except Exception as e:
            error = str(e)
            print(f"  ❌ FAILED: {error[:150]}\n")
            
            if "429" in error or "quota" in error.lower():
                print("  💡 This is a rate limit - you're hitting 15 req/min")
                print("  💡 Wait 60 seconds and try again")
                print("  💡 This means the model DOES work, just rate limited!\n")

if __name__ == "__main__":
    asyncio.run(test_gemini_25())


================================================
FILE: test_providers.py
================================================
"""
Test all LLM providers to ensure they work correctly.

Usage:
    python test_providers.py
    python test_providers.py --provider gemini
    python test_providers.py --stream
"""
import asyncio
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.gemini_provider import GeminiProvider


async def test_provider(provider_name: str, streaming: bool = False):
    """Test a specific provider"""
    
    print(f"\n{'='*60}")
    print(f"Testing {provider_name.upper()}")
    print(f"Mode: {'Streaming' if streaming else 'Non-streaming'}")
    print(f"{'='*60}\n")
    
    # Create provider
    if provider_name == "openai":
        provider = OpenAIProvider()
        model = "gpt-3.5-turbo"
    elif provider_name == "anthropic":
        provider = AnthropicProvider()
        model = "claude-3-haiku-20240307"
    elif provider_name == "gemini":
        provider = GeminiProvider()
        model = "gemini-2.5-flash"
        # If provider auto-detected a model, show it
        try:
            auto = getattr(provider, 'auto_model_actual', None)
            if auto:
                print(f"Detected Gemini model for this key: {auto}")
        except Exception:
            pass
    else:
        print(f"❌ Unknown provider: {provider_name}")
        return False
    
    prompt = "Say 'Hello! I am working correctly.' in exactly those words."
    
    try:
        if streaming:
            print("🔄 Streaming response:")
            print("-" * 40)
            chunks = []
            async for chunk in provider.stream_generate(prompt, model=model, max_tokens=50):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            
            full_response = "".join(chunks)
            print("\n" + "-" * 40)
            print(f"✅ Received {len(chunks)} chunks")
            print(f"✅ Total length: {len(full_response)} characters")
            
        else:
            print("📥 Generating full response...")
            result = await provider.generate(prompt, model=model, max_tokens=50)
            
            print("-" * 40)
            print(f"Response: {result['content']}")
            print("-" * 40)
            print(f"✅ Model: {result['model']}")
            print(f"✅ Prompt tokens: {result['prompt_tokens']}")
            print(f"✅ Completion tokens: {result['completion_tokens']}")
            print(f"✅ Total tokens: {result['total_tokens']}")
            
            # Test cost estimation
            cost = provider.estimate_cost(
                result['prompt_tokens'],
                result['completion_tokens'],
                model
            )
            print(f"✅ Estimated cost: ${cost:.6f}")
        
        print(f"\n✅ {provider_name.upper()} test PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ {provider_name.upper()} test FAILED")
        print(f"Error: {str(e)}\n")
        return False


async def test_all_providers(streaming: bool = False):
    """Test all available providers"""
    
    providers = ["gemini", "openai", "anthropic"]
    results = {}
    
    print("\n" + "="*60)
    print("Testing All LLM Providers")
    print("="*60)
    
    for provider_name in providers:
        results[provider_name] = await test_provider(provider_name, streaming)
        await asyncio.sleep(2)  # Rate limiting buffer
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for provider_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{provider_name.upper():12} {status}")
    
    print("\n")
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    if passed_count == total_count:
        print(f"🎉 All {total_count} providers working!")
    else:
        print(f"⚠️ {passed_count}/{total_count} providers working")
        print("\nFailed providers may need:")
        print("  - API key in .env file")
        print("  - pip install <package>")
        print("  - Valid API credits")


async def check_api_keys():
    """Check which API keys are configured"""
    import os
    
    print("\n" + "="*60)
    print("API Key Configuration Check")
    print("="*60 + "\n")
    
    keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }
    
    for key_name, key_value in keys.items():
        if key_value:
            # Show first/last 4 chars
            masked = f"{key_value[:8]}...{key_value[-4:]}" if len(key_value) > 12 else "****"
            print(f"✅ {key_name:20} configured ({masked})")
        else:
            print(f"❌ {key_name:20} NOT FOUND")
    
    print()


def main():
    parser = argparse.ArgumentParser(description="Test LLM providers")
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "anthropic", "all"],
        default="all",
        help="Which provider to test"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Test streaming mode"
    )
    parser.add_argument(
        "--check-keys",
        action="store_true",
        help="Only check API key configuration"
    )
    
    args = parser.parse_args()
    
    if args.check_keys:
        asyncio.run(check_api_keys())
        return
    
    if args.provider == "all":
        asyncio.run(test_all_providers(streaming=args.stream))
    else:
        asyncio.run(test_provider(args.provider, streaming=args.stream))


if __name__ == "__main__":
    main()



================================================
FILE: tsconfig.json
================================================
{
  "compilerOptions": {
    "lib": [
      "dom",
      "dom.iterable",
      "esnext"
    ],
    "allowJs": true,
    "target": "ES6",
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": [
        "./*"
      ]
    }
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts",
    ".next/dev/types/**/*.ts"
  ],
  "exclude": [
    "node_modules"
  ]
}



================================================
FILE: ws_demo.py
================================================
"""Simple Python WebSocket demo to test the /ws/chat endpoint.

Requires: `websockets` package (pip install websockets)

Usage:
    python ws_demo.py

This script connects, sends a single chat message, prints incoming chunks and the final done message.
"""

try:
    import websockets
except Exception as e:
    print("Please install the 'websockets' package: pip install websockets")
    raise

SERVER = os.getenv('SERVER', 'ws://localhost:8000/ws/chat')
USER_ID = os.getenv('DEMO_USER', 'demo-user-1')
MODEL = os.getenv('DEMO_MODEL', 'gemini-2.5-flash')
PROMPT = os.getenv('DEMO_PROMPT', "Write a short haiku about coding")




"""
WebSocket demo disabled.

This project now uses HTTP SSE streaming at `/stream/chat`. The old `ws_demo.py` is left here for reference but is disabled.
"""
print("ws_demo.py is disabled. Use the HTTP-SSE test client at /test_client.html or run provider tests.")
if __name__ == '__main__':
    asyncio.run(run())



================================================
FILE: app/__init__.py
================================================
"""App package for the Fiesta project"""

__all__ = [
    "config",
    "schemas",
    "models",
    "dependencies",
    "llm",
    "routers",
]



================================================
FILE: app/config.py
================================================
import os
from typing import List, Optional
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        # remove surrounding quotes
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        # only set if not present in env already
        if key not in os.environ:
            os.environ[key] = val


def _parse_list(value: str) -> List[str]:
    value = value.strip()
    if not value:
        return []
    # simple formats: comma separated or python list like ["*", "http://...]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        # split by comma and strip quotes/spaces
        items = []
        for part in inner.split(","):
            p = part.strip()
            if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")):
                p = p[1:-1]
            if p:
                items.append(p)
        return items
    # else comma separated
    return [p.strip() for p in value.split(",") if p.strip()]


_load_dotenv()


class Settings:
    def __init__(self):
        self.app_name: str = os.getenv("APP_NAME", "LLM Streaming Backend API")
        self.version: str = os.getenv("VERSION", "0.1.0")
        self.docs_url: str = os.getenv("DOCS_URL", "/docs")
        self.redoc_url: str = os.getenv("REDOC_URL", "/redoc")
        self.cors_allow_origins: List[str] = _parse_list(os.getenv("CORS_ALLOW_ORIGINS", "[\"*\"]"))

        # Demo user defaults (for development)
        self.demo_user_email: str = os.getenv("DEMO_USER_EMAIL", "demo@example.com")
        self.demo_user_username: str = os.getenv("DEMO_USER_USERNAME", "demo_user")
        self.demo_user_password: str = os.getenv("DEMO_USER_PASSWORD", "demo123")
        # Provider API keys (optional)
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        # Gemima / provider feature flags
        self.gemini_force_non_streaming: bool = os.getenv("GEMINI_FORCE_NON_STREAMING", "").lower() in ("1", "true", "yes")
        self.enable_ws_streaming: bool = os.getenv("ENABLE_WS_STREAMING", "false").lower() in ("1", "true", "yes")


settings = Settings()



================================================
FILE: app/dependencies.py
================================================
from fastapi import HTTPException
from typing import Dict
from datetime import datetime, timedelta
from collections import defaultdict

from . import models


def get_user_or_404(user_id: str) -> Dict:
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return models.users_db[user_id]


def get_subscription_or_404_by_user(user_id: str) -> Dict:
    for sub in models.subscriptions_db.values():
        if sub["user_id"] == user_id:
            return sub
    raise HTTPException(status_code=404, detail="Subscription not found")


def check_subscription_active(subscription: Dict) -> None:
    """Verify subscription is active and not expired"""
    if subscription["status"] != "active":
        raise HTTPException(status_code=403, detail=f"Subscription is {subscription['status']}")
    if subscription.get("expires_at") and datetime.now() > subscription["expires_at"]:
        raise HTTPException(status_code=403, detail="Subscription expired")


def check_model_access(subscription: Dict, model: str) -> None:
    """Verify user has access to the requested model"""
    if model not in subscription.get("allowed_models", []):
        raise HTTPException(
            status_code=403,
            detail=f"Model {model} not available in {subscription['tier_name']} tier. Available: {subscription['allowed_models']}"
        )


def check_tokens_available(subscription: Dict, estimated_tokens: int) -> None:
    """Verify user has enough tokens"""
    if subscription["tokens_remaining"] < estimated_tokens:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient tokens. Required: {estimated_tokens}, Available: {subscription['tokens_remaining']}"
        )


def deduct_tokens(subscription: Dict, tokens_used: int) -> None:
    """Deduct tokens from user's subscription"""
    subscription["tokens_used"] += tokens_used
    subscription["tokens_remaining"] -= tokens_used


def check_credits_available(subscription: Dict, estimated_llm_tokens: int, model: str) -> None:
    """Verify user has enough credits for the estimated LLM tokens for the given model."""
    multiplier = models.MODEL_CREDIT_COSTS.get(model, models.MODEL_CREDIT_COSTS.get("default", 0.01))
    estimated_credits = int(estimated_llm_tokens * multiplier)
    if subscription.get("credits_remaining", 0) < estimated_credits:
        raise HTTPException(
            status_code=402,
            detail=(f"Insufficient credits. Required: {estimated_credits} (est), "
                    f"Available: {subscription.get('credits_remaining', 0)}")
        )


def deduct_credits(subscription: Dict, llm_tokens: int, model: str) -> int:
    """Deduct credits from user's subscription based on LLM tokens and model multiplier.

    Returns the number of credits deducted.
    """
    multiplier = models.MODEL_CREDIT_COSTS.get(model, models.MODEL_CREDIT_COSTS.get("default", 0.01))
    credits_to_deduct = int(llm_tokens * multiplier)
    # Ensure we don't go negative
    credits_to_deduct = min(credits_to_deduct, subscription.get("credits_remaining", 0))
    subscription["credits_used"] = subscription.get("credits_used", 0) + credits_to_deduct
    subscription["credits_remaining"] = subscription.get("credits_remaining", 0) - credits_to_deduct
    return credits_to_deduct


def track_api_cost(user_id: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
    """Track API costs for billing and analytics"""
    cost_id = str(__import__('uuid').uuid4())
    models.cost_tracker_db[cost_id] = {
        "id": cost_id,
        "user_id": user_id,
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": cost_usd,
        "created_at": datetime.now(),
    }
    
    # Also accumulate in subscription's monthly cost
    subscription = get_subscription_or_404_by_user(user_id)
    subscription["monthly_api_cost_usd"] += cost_usd


def track_real_api_usage(user_id: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
    """Track real API usage (actual calls to external APIs)"""
    if user_id not in models.api_usage_db:
        models.api_usage_db[user_id] = {}
    
    if provider not in models.api_usage_db[user_id]:
        models.api_usage_db[user_id][provider] = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "models_used": set(),
            "last_used": None,
        }
    
    usage = models.api_usage_db[user_id][provider]
    usage["calls"] += 1
    usage["prompt_tokens"] += prompt_tokens
    usage["completion_tokens"] += completion_tokens
    usage["total_tokens"] += prompt_tokens + completion_tokens
    usage["cost_usd"] += cost_usd
    usage["last_used"] = datetime.now()
    if model not in usage["models_used"]:
        usage["models_used"].add(model)


def get_user_cost_summary(user_id: str) -> Dict:
    """Get total API costs for a user"""
    user_costs = [c for c in models.cost_tracker_db.values() if c["user_id"] == user_id]
    total_tokens = sum(c["total_tokens"] for c in user_costs)
    total_cost = sum(c["cost_usd"] for c in user_costs)
    return {
        "user_id": user_id,
        "total_api_calls": len(user_costs),
        "total_tokens_consumed": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "breakdown_by_provider": _breakdown_by_provider(user_costs),
    }


def _breakdown_by_provider(costs: list) -> Dict:
    breakdown = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
    for cost in costs:
        provider = cost["provider"]
        breakdown[provider]["calls"] += 1
        breakdown[provider]["tokens"] += cost["total_tokens"]
        breakdown[provider]["cost"] += cost["cost_usd"]
    return {k: {**v, "cost": round(v["cost"], 4)} for k, v in breakdown.items()}


def get_real_api_usage_summary(user_id: str) -> Dict:
    """Get real API usage summary for a user"""
    if user_id not in models.api_usage_db:
        return {
            "user_id": user_id,
            "total_api_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "by_provider": {},
        }
    
    user_usage = models.api_usage_db[user_id]
    total_calls = sum(p["calls"] for p in user_usage.values())
    total_tokens = sum(p["total_tokens"] for p in user_usage.values())
    total_cost = sum(p["cost_usd"] for p in user_usage.values())
    
    by_provider = {}
    for provider, data in user_usage.items():
        by_provider[provider] = {
            "calls": data["calls"],
            "prompt_tokens": data["prompt_tokens"],
            "completion_tokens": data["completion_tokens"],
            "total_tokens": data["total_tokens"],
            "cost_usd": round(data["cost_usd"], 4),
            "models_used": list(data["models_used"]),
            "last_used": data["last_used"].isoformat() if data["last_used"] else None,
        }
    
    return {
        "user_id": user_id,
        "total_api_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "by_provider": by_provider,
    }


# Request rate limiting (in-memory for now)
rate_limiter = defaultdict(list)  # {user_id: [timestamps]}


def check_rate_limit(user_id: str, rate_limit_per_minute: int) -> None:
    """Check if user exceeds rate limit"""
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old entries
    rate_limiter[user_id] = [ts for ts in rate_limiter[user_id] if ts > minute_ago]
    
    if len(rate_limiter[user_id]) >= rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {rate_limit_per_minute} requests per minute"
        )
    
    # Add current request
    rate_limiter[user_id].append(now)


# Conversation/message stores for later phases
conversations_db = {}
messages_db = {}




================================================
FILE: app/globals.css
================================================
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

:root {
  --background: oklch(0.98 0.002 247.858);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.508 0.237 288.63);
  --primary-foreground: oklch(1 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.92 0.005 253.85);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.508 0.237 288.63);
  --accent-foreground: oklch(1 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --destructive-foreground: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.508 0.237 288.63);
  --chart-1: oklch(0.508 0.237 288.63);
  --chart-2: oklch(0.6 0.118 184.704);
  --chart-3: oklch(0.398 0.07 227.392);
  --chart-4: oklch(0.828 0.189 84.429);
  --chart-5: oklch(0.769 0.188 70.08);
  --radius: 0.625rem;
  --sidebar: oklch(0.96 0.004 253.45);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.508 0.237 288.63);
  --sidebar-primary-foreground: oklch(1 0 0);
  --sidebar-accent: oklch(0.95 0.01 254);
  --sidebar-accent-foreground: oklch(0.508 0.237 288.63);
  --sidebar-border: oklch(0.92 0.005 253.85);
  --sidebar-ring: oklch(0.508 0.237 288.63);
}

.dark {
  --background: oklch(0.08 0 0);
  --foreground: oklch(0.97 0.001 254);
  --card: oklch(0.12 0.002 254);
  --card-foreground: oklch(0.97 0.001 254);
  --popover: oklch(0.12 0.002 254);
  --popover-foreground: oklch(0.97 0.001 254);
  --primary: oklch(0.7 0.22 289);
  --primary-foreground: oklch(0.08 0 0);
  --secondary: oklch(0.22 0.005 254);
  --secondary-foreground: oklch(0.97 0.001 254);
  --muted: oklch(0.25 0.003 254);
  --muted-foreground: oklch(0.708 0 0);
  --accent: oklch(0.7 0.22 289);
  --accent-foreground: oklch(0.08 0 0);
  --destructive: oklch(0.396 0.141 25.723);
  --destructive-foreground: oklch(0.637 0.237 25.331);
  --border: oklch(0.25 0.003 254);
  --input: oklch(0.2 0.002 254);
  --ring: oklch(0.7 0.22 289);
  --chart-1: oklch(0.7 0.22 289);
  --chart-2: oklch(0.696 0.17 162.48);
  --chart-3: oklch(0.769 0.188 70.08);
  --chart-4: oklch(0.627 0.265 303.9);
  --chart-5: oklch(0.645 0.246 16.439);
  --sidebar: oklch(0.11 0.002 254);
  --sidebar-foreground: oklch(0.97 0.001 254);
  --sidebar-primary: oklch(0.7 0.22 289);
  --sidebar-primary-foreground: oklch(0.08 0 0);
  --sidebar-accent: oklch(0.2 0.005 254);
  --sidebar-accent-foreground: oklch(0.7 0.22 289);
  --sidebar-border: oklch(0.2 0.005 254);
  --sidebar-ring: oklch(0.7 0.22 289);
}

@theme inline {
  --font-sans: "Geist", "Geist Fallback";
  --font-mono: "Geist Mono", "Geist Mono Fallback";
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}

@layer utilities {
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  .gradient-text {
    @apply bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent;
  }
}




================================================
FILE: app/layout.tsx
================================================
import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import "./globals.css"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "AI Fiesta",
  description: "Multi-model AI chat with token and credit tracking",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`font-sans antialiased`}>
        {children}
        <Analytics />
      </body>
    </html>
  )
}




================================================
FILE: app/loading.tsx
================================================
export default function Loading() {
  return null
}




================================================
FILE: app/models.py
================================================
"""In-memory data structures and helper functions.
This will be replaced by real database models later.
"""
import uuid
from datetime import datetime
from typing import Dict

# In-memory stores
users_db: Dict[str, dict] = {}
subscriptions_db: Dict[str, dict] = {}
cost_tracker_db: Dict[str, dict] = {}  # track API costs per user
api_usage_db: Dict[str, dict] = {}  # track real API usage per user per provider

# Subscription tier definitions
SUBSCRIPTION_TIERS = {
    "free": {
        "tier_id": "free",
        "name": "Free",
        # Allow the lower-cost / flash Gemini model on the free tier
        "allowed_models": ["gemini-2.5-flash", "mock-gpt4"],
        "tokens_per_month": 1000,
        "credits_per_month": 1000,
        "rate_limit_per_minute": 10,
        "cost_usd": 0.0,
    },
    "pro": {
        "tier_id": "pro",
        "name": "Pro",
        "allowed_models": [
            "gpt-3.5-turbo",
            "claude-3-haiku-20240307",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
        ],
        "tokens_per_month": 100000,
        "credits_per_month": 50000,
        "rate_limit_per_minute": 100,
        "cost_usd": 29.99,
    },
    "enterprise": {
        "tier_id": "enterprise",
        "name": "Enterprise",
        "allowed_models": [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-5",
            "gpt-5.1",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "gemini-2.5-pro",
            "gpt-3.5-turbo",
        ],
        "tokens_per_month": 1000000,
        "credits_per_month": 1000000,
        "rate_limit_per_minute": 1000,
        "cost_usd": 299.99,
    },
}


def create_default_subscription(user_id: str, plan: str = "free") -> dict:
    """Create a default subscription for a new user"""
    tier = SUBSCRIPTION_TIERS.get(plan, SUBSCRIPTION_TIERS["free"])
    
    subscription = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "tier_id": tier["tier_id"],
        "tier_name": tier["name"],
        "plan_type": plan,
        "status": "active",
        "allowed_models": tier["allowed_models"],
        "tokens_limit": tier["tokens_per_month"],
        "tokens_used": 0,
        "tokens_remaining": tier["tokens_per_month"],
        "credits_limit": tier.get("credits_per_month", tier["tokens_per_month"]),
        "credits_used": 0,
        "credits_remaining": tier.get("credits_per_month", tier["tokens_per_month"]),
        "monthly_cost_usd": tier["cost_usd"],
        "monthly_api_cost_usd": 0.0,  # tracks actual API spend
        "rate_limit_per_minute": tier["rate_limit_per_minute"],
        "created_at": datetime.now(),
        "expires_at": None,  # can set for trial periods
    }
    subscriptions_db[subscription["id"]] = subscription
    return subscription


# Per-model credit cost multipliers. These represent credits charged per LLM token
# (multiplier). Adjust values according to your pricing strategy.
MODEL_CREDIT_COSTS = {
    "gpt-4": 0.06,           # 0.06 credits per token (example)
    "gpt-4-turbo": 0.05,
    "gpt-5": 0.1,
    "gpt-3.5-turbo": 0.01,
    "gpt-5.1": 0.12,
    "claude-3-haiku-20240307": 0.02,
    "claude-3-opus-20240229": 0.03,
    "gemini-2.5-pro": 0.04,
    "gemini-2.5-flash": 0.005,
    # fallback/default multiplier
    "default": 0.01,
}




================================================
FILE: app/page.tsx
================================================
"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatMessage } from "@/components/chat-message"
import { ModelSelector } from "@/components/model-selector"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { useChatSSE } from "@/hooks/use-chat-sse"
import { getTokenUsage, getSubscription } from "@/lib/api"
import { Zap, Send, AlertCircle, Sparkles } from "lucide-react"

const DEMO_USER_ID = process.env.NEXT_PUBLIC_DEFAULT_USER_ID || "demo-user-1"

export default function ChatPage() {
  const [selectedModel, setSelectedModel] = useState("")
  const [inputValue, setInputValue] = useState("")
  const [usage, setUsage] = useState<any>(null)
  const [subscription, setSubscription] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [loadingUsage, setLoadingUsage] = useState(false)

  const { messages, sendMessage, isStreaming, error } = useChatSSE(DEMO_USER_ID)

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [usageData, subData] = await Promise.all([getTokenUsage(DEMO_USER_ID), getSubscription(DEMO_USER_ID)])
        setUsage(usageData)
        setSubscription(subData)
      } catch (err) {
        console.error("Failed to fetch initial data:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchInitialData()
  }, [])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isStreaming) return

    const message = inputValue
    setInputValue("")
    setLoadingUsage(true)

    await sendMessage(message, selectedModel || "gemini-2.5-flash", (delta) => {
      setUsage((prev) =>
        prev
          ? {
              ...prev,
              tokens_remaining: delta.tokens_remaining,
              credits_remaining: delta.credits_remaining,
            }
          : null,
      )
    })

    setLoadingUsage(false)
  }

  const handleNewChat = () => {
    // In a real app, this would reset the conversation
    setInputValue("")
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar onNewChat={handleNewChat} />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="border-b border-border bg-card/50 backdrop-blur-sm p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="font-semibold flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                AI Fiesta
              </h1>
              <p className="text-xs text-muted-foreground">Multi-Model AI Chat</p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            {usage && (
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Tokens</p>
                  <p className="font-semibold text-sm">
                    {usage.tokens_remaining}/{usage.tokens_limit}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Credits</p>
                  <p className="font-semibold text-sm">
                    {usage.credits_remaining}/{usage.credits_limit}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-6 no-scrollbar">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-6">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mx-auto mb-3">
                  <Sparkles className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-semibold mb-2">Start a conversation</h2>
                <p className="text-muted-foreground text-sm">
                  Pick a model, type a prompt, and we’ll stream the response in real-time.
                </p>
              </div>

              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {[
                  "Summarize this article into 3 bullets",
                  "Explain transformers like I’m 12",
                  "Draft a welcome email for new users",
                  "Brainstorm product taglines",
                ].map((prompt) => (
                  <Button
                    key={prompt}
                    variant="outline"
                    size="sm"
                    onClick={() => setInputValue(prompt)}
                    className="whitespace-nowrap"
                  >
                    {prompt}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto">
              {messages.map((msg, idx) => (
                <ChatMessage key={msg.id} message={msg} isStreaming={isStreaming && idx === messages.length - 1} />
              ))}
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="px-6 py-3 bg-destructive/10 border border-destructive/20 rounded-lg mx-6 flex items-gap-2 gap-2">
            <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-border bg-card/50 backdrop-blur-sm p-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {/* Model Selector and Options */}
            <div className="flex flex-col md:flex-row items-center gap-3">
              <ModelSelector value={selectedModel} onChange={setSelectedModel} userTier={subscription?.tier_id} />

              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="gap-1 hidden md:flex">
                  <Zap className="w-3 h-3" />
                  Super Fiesta
                </Badge>
              </div>
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSendMessage} className="flex gap-3">
              <Input
                placeholder="Ask me anything..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isStreaming}
                className="flex-1"
              />
              <Button type="submit" disabled={isStreaming || !inputValue.trim()} size="icon" className="rounded-full">
                <Send className="w-4 h-4" />
              </Button>
            </form>

          </div>
        </div>
      </div>
    </div>
  )
}




================================================
FILE: app/schemas.py
================================================
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_type: str
    status: str
    tokens_limit: int
    tokens_used: int
    tokens_remaining: int
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None


class TokenUsageResponse(BaseModel):
    tokens_used: int
    tokens_remaining: int
    tokens_limit: int
    percentage_used: float
    credits_used: int | None = None
    credits_remaining: int | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str


class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = "mock"
    conversation_id: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class ChatResponse(BaseModel):
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    content: str | None = None
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    tokens_remaining: Optional[int] = None
    credits_used: Optional[int] = None
    credits_remaining: Optional[int] = None
    credits_used: Optional[int] = None
    credits_remaining: Optional[int] = None


class Conversation(BaseModel):
    id: str
    user_id: str
    created_at: datetime


class Message(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    tokens: int
    created_at: datetime


class SubscriptionTier(BaseModel):
    """Subscription tier with model access and token limits"""
    tier_id: str
    name: str  # "free", "pro", "enterprise"
    allowed_models: list[str]  # e.g. ["gemini-pro"], ["gpt-3.5-turbo", "claude-3-haiku"], etc
    tokens_per_month: int
    rate_limit_per_minute: int
    cost_usd: float  # monthly cost


class CostTracker(BaseModel):
    """Track API costs per provider and per user"""
    user_id: str
    provider: str  # "openai", "anthropic", "gemini"
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    created_at: datetime


class SubscriptionDetail(BaseModel):
    """User subscription with tier info and usage"""
    id: str
    user_id: str
    tier_id: str
    tier_name: str
    allowed_models: list[str]
    tokens_limit: int
    tokens_used: int
    tokens_remaining: int
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None
    monthly_cost_usd: float
    monthly_api_cost_usd: float
    requests_this_minute: int
    status: str  # "active", "expired", "suspended"
    created_at: datetime
    expires_at: Optional[datetime]




================================================
FILE: app/admin/page.tsx
================================================
"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  getAdminStats,
  getAllSubscriptions,
  addTokens,
  addCredits,
  upgradeSubscription,
  type AdminStats,
  type Subscription,
} from "@/lib/api"
import { ArrowLeft, Users, Zap, CreditCard, TrendingUp } from "lucide-react"

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [selectedUser, setSelectedUser] = useState<string>("")
  const [tokensToAdd, setTokensToAdd] = useState<string>("")
  const [creditsToAdd, setCreditsToAdd] = useState<string>("")
  const [upgradeTier, setUpgradeTier] = useState<string>("pro")

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, subsData] = await Promise.all([getAdminStats(), getAllSubscriptions()])
        setStats(statsData)
        setSubscriptions(subsData)
        if (subsData.length > 0) {
          setSelectedUser(subsData[0].user_id)
        }
      } catch (err) {
        console.error("Failed to fetch admin data:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const refreshSubs = async () => {
    const subs = await getAllSubscriptions()
    setSubscriptions(subs)
    if (!selectedUser && subs.length > 0) setSelectedUser(subs[0].user_id)
  }

  const handleAddTokens = async () => {
    if (!selectedUser || !tokensToAdd) return
    setBusy(true)
    try {
      await addTokens(selectedUser, Number(tokensToAdd))
      await refreshSubs()
      setTokensToAdd("")
    } catch (err) {
      console.error("Failed to add tokens", err)
    } finally {
      setBusy(false)
    }
  }

  const handleAddCredits = async () => {
    if (!selectedUser || !creditsToAdd) return
    setBusy(true)
    try {
      await addCredits(selectedUser, Number(creditsToAdd))
      await refreshSubs()
      setCreditsToAdd("")
    } catch (err) {
      console.error("Failed to add credits", err)
    } finally {
      setBusy(false)
    }
  }

  const handleUpgrade = async () => {
    if (!selectedUser || !upgradeTier) return
    setBusy(true)
    try {
      await upgradeSubscription(selectedUser, upgradeTier)
      await refreshSubs()
    } catch (err) {
      console.error("Failed to upgrade subscription", err)
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-2">🎉 AI Fiesta Admin</h1>
              <p className="text-muted-foreground">Dashboard and management</p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {stats &&
            [
              {
                title: "Total Users",
                value: stats.total_users_with_usage,
                icon: Users,
              },
              {
                title: "API Calls",
                value: stats.total_api_calls_made.toLocaleString(),
                icon: TrendingUp,
              },
              {
                title: "Tokens Used",
                value: (stats.total_tokens_consumed / 1000).toFixed(1) + "K",
                icon: Zap,
              },
              {
                title: "Total Cost",
                value: "$" + stats.total_cost_usd.toFixed(2),
                icon: CreditCard,
              },
            ].map((stat, idx) => {
              const Icon = stat.icon
              return (
                <Card key={idx} className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{stat.title}</p>
                      <p className="text-2xl font-bold mt-2">{stat.value}</p>
                    </div>
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Icon className="w-6 h-6 text-primary" />
                    </div>
                  </div>
                </Card>
              )
            })}
        </div>

        {/* Provider Usage */}
        {stats && Object.keys(stats.by_provider).length > 0 && (
          <Card className="p-6 mb-8">
            <h2 className="text-lg font-semibold mb-4">Usage by Provider</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(stats.by_provider).map(([provider, data]) => (
                <div key={provider} className="bg-muted/50 rounded-lg p-4">
                  <p className="font-semibold capitalize mb-3">{provider}</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Calls:</span>
                      <span className="font-medium">{data.calls}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Tokens:</span>
                      <span className="font-medium">{(data.tokens / 1000).toFixed(1)}K</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Cost:</span>
                      <span className="font-medium">${data.cost.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Users Table */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">Users & Subscriptions</h2>
          <div className="mb-4 grid gap-3 md:grid-cols-3">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Select user</label>
              <select
                className="border rounded-md px-3 py-2 bg-background"
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
              >
                {subscriptions.map((sub) => (
                  <option key={sub.user_id} value={sub.user_id}>
                    {sub.user_id} ({sub.tier_name})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Add tokens</label>
              <div className="flex gap-2">
                <input
                  className="flex-1 border rounded-md px-3 py-2 bg-background"
                  type="number"
                  min="1"
                  value={tokensToAdd}
                  onChange={(e) => setTokensToAdd(e.target.value)}
                  placeholder="e.g. 1000"
                />
                <Button variant="outline" disabled={busy || !tokensToAdd} onClick={handleAddTokens}>
                  Add
                </Button>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Add credits</label>
              <div className="flex gap-2">
                <input
                  className="flex-1 border rounded-md px-3 py-2 bg-background"
                  type="number"
                  min="1"
                  value={creditsToAdd}
                  onChange={(e) => setCreditsToAdd(e.target.value)}
                  placeholder="e.g. 500"
                />
                <Button variant="outline" disabled={busy || !creditsToAdd} onClick={handleAddCredits}>
                  Add
                </Button>
              </div>
            </div>

            <div className="flex flex-col gap-2 md:col-span-3">
              <label className="text-sm font-medium">Upgrade tier</label>
              <div className="flex flex-col md:flex-row gap-2">
                <select
                  className="border rounded-md px-3 py-2 bg-background md:w-48"
                  value={upgradeTier}
                  onChange={(e) => setUpgradeTier(e.target.value)}
                >
                  <option value="free">Free</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                <Button variant="outline" disabled={busy} onClick={handleUpgrade}>
                  Upgrade
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Uses existing endpoints: add tokens/credits and tier upgrade are executed immediately.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Tokens Used</TableHead>
                  <TableHead>Credits Used</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subscriptions.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell className="font-medium">{sub.user_id}</TableCell>
                    <TableCell>
                      <div className="capitalize text-sm font-medium">{sub.tier_name}</div>
                    </TableCell>
                    <TableCell className="text-sm">
                      {sub.tokens_used.toLocaleString()} / {sub.tokens_limit.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm">
                      {sub.credits_used.toLocaleString()} / {sub.credits_limit.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div
                        className={`text-xs font-semibold px-2 py-1 rounded-full w-fit ${
                          sub.status === "active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                        }`}
                      >
                        {sub.status}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>
    </div>
  )
}




================================================
FILE: app/llm/__init__.py
================================================
"""LLM provider package"""

__all__ = ["base", "mock"]



================================================
FILE: app/llm/anthropic_provider.py
================================================
from typing import Optional, AsyncIterator
import os
import asyncio

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.utils.stream_emulation import emulate_stream_text

try:
    from anthropic import AsyncAnthropic
except Exception:
    AsyncAnthropic = None


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = AsyncAnthropic(api_key=api_key) if AsyncAnthropic is not None else None
        self.provider_name = "anthropic"

    async def generate(self, prompt: str, model: str = "claude-3-haiku-20240307", max_tokens: int = 1000, temperature: float = 0.7) -> dict:
        if self.client is None:
            raise Exception("Anthropic client not available (library not installed)")
        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return {
                "content": response.content[0].text if hasattr(response, 'content') else getattr(response, 'text', ""),
                "model": getattr(response, "model", model),
                "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                "completion_tokens": getattr(response.usage, "output_tokens", 0),
                "total_tokens": getattr(response.usage, "input_tokens", 0) + getattr(response.usage, "output_tokens", 0),
            }
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    async def stream_generate(self, prompt: str, model: str = "claude-3-haiku-20240307", max_tokens: int = 1000, temperature: float = 0.7) -> AsyncIterator[str]:
        if self.client is None:
            raise Exception("Anthropic client not available (library not installed)")
        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception:
            # Fallback to non-streaming generate and emulate streaming
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content', '') if isinstance(result, dict) else str(result)
                async for part in emulate_stream_text(content):
                    yield part
            except Exception:
                return

    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "anthropic")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        prices = {
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
        }
        base_model = "claude-3-haiku"
        for key in prices.keys():
            if key in model:
                base_model = key
                break
        pricing = prices[base_model]
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return input_cost + output_cost



================================================
FILE: app/llm/base.py
================================================
from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    Provides both synchronous-like (awaitable) full-response generation and
    async streaming generation. Providers should implement both so callers can
    choose the appropriate mode.
    """

    @abstractmethod
    async def generate(self, prompt: str, model: str = "mock", **kwargs) -> dict:
        """Asynchronously generate a full response for the given prompt.

        Returns a dict with at least: {
            "content": str,
            "model": str,
            "prompt_tokens": int,
            "completion_tokens": int,
            "total_tokens": int,
        }
        """

    @abstractmethod
    async def stream_generate(self, prompt: str, model: str = "mock", **kwargs) -> AsyncIterator[str]:
        """Asynchronously stream the response. Yields string chunks as they arrive."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Return token count for a given text"""

    @abstractmethod
    def estimate_cost(self, *args, **kwargs) -> float:
        """Estimate cost for a request. Signature left generic for provider flexibility."""



================================================
FILE: app/llm/factory.py
================================================
"""
LLM Provider Factory

Returns a provider instance based on model name.
"""

from typing import Optional

from app.llm.base import BaseLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.mock import MockLLMProvider  # you may modify/remove this


class LLMProviderFactory:
    """
    Returns the correct provider based on the model name.
    """

    @staticmethod
    def create_provider(model: str) -> BaseLLMProvider:
        """
        Picks provider based on model string:
        - "gpt-4", "gpt-4o-mini", etc → OpenAI
        - "claude-3-pro", etc → Anthropic
        - "gemini-2.5-pro", "gemini-flash" → Gemini
        """
        model_lower = (model or "").lower()

        if any(key in model_lower for key in ["gpt", "o1-mini", "openai"]):
            return OpenAIProvider()

        if "claude" in model_lower:
            return AnthropicProvider()

        if "gemini" in model_lower:
            return GeminiProvider()

        # fallback
        return MockLLMProvider()

    @staticmethod
    def get_available_models() -> dict:
        """
        List supported models for each provider.
        """
        return {
            "openai": [
                "gpt-4o-mini",
                "gpt-4.1",
                "gpt-4o",
                "gpt-3.5-turbo",
            ],
            "anthropic": [
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229",
                "claude-3-opus-20240229",
            ],
            "gemini": [
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-pro-latest",
                "gemini-flash-latest",
            ],
            "mock": [
                "mock-gpt",
                "mock-claude",
            ],
        }


llm_factory = LLMProviderFactory()



================================================
FILE: app/llm/gemini_provider.py
================================================
"""
Gemini Provider – Correct implementation with full BaseLLMProvider compliance.

Implements:
- generate()
- stream_generate()    <-- required by BaseLLMProvider
- estimate_cost()      <-- required by BaseLLMProvider
"""

from typing import AsyncIterator, Optional
import os

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GENAI_PRESENT = True
except Exception:
    genai = None
    google_exceptions = None
    GENAI_PRESENT = False

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.config import settings


class GeminiProvider(BaseLLMProvider):
    name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        # Read API key from explicit arg, settings, or environment.
        self.api_key = api_key or getattr(settings, "gemini_api_key", None) or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not configured.")
        # Public provider identifier used by tracking and analytics
        self.provider_name = "gemini"
        if not GENAI_PRESENT:
            raise RuntimeError("google-generativeai SDK not installed. Install with: pip install google-generativeai google-api-core")

        genai.configure(api_key=self.api_key)

    # -----------------------------------------------------
    # Model Resolution
    # -----------------------------------------------------
    def _resolve_model(self, model: Optional[str]) -> str:
        """Convert 'gemini-2.5-flash' → 'models/gemini-2.5-flash'."""
        if not model:
            model = self.default_model

        if model.startswith("models/"):
            return model

        return f"models/{model}"

    # -----------------------------------------------------
    # Response Extraction
    # -----------------------------------------------------
    def _extract_text(self, obj) -> str:
        """Extract text from Gemini objects (stream or non-stream)."""
        if not hasattr(obj, "candidates"):
            return ""

        parts = []
        for cand in obj.candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue

            for part in getattr(content, "parts", []):
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)

        return "".join(parts).strip()

    # -----------------------------------------------------
    # Non-Streaming Generate
    # -----------------------------------------------------
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:

        actual = self._resolve_model(model)
        model_obj = genai.GenerativeModel(actual)

        response = await model_obj.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )

        text = self._extract_text(response)

        return {
            "content": text,
            "model": actual,
            "prompt_tokens": token_counter.count_tokens(prompt, "gemini"),
            "completion_tokens": token_counter.count_tokens(text, "gemini"),
        }

    # -----------------------------------------------------
    # Streaming Generate (BaseLLMProvider requirement)
    # -----------------------------------------------------
    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[str]:

        actual = self._resolve_model(model)
        model_obj = genai.GenerativeModel(actual)

        try:
            stream = await model_obj.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
                stream=True,
            )
        except Exception as e:
            # If this looks like a quota or rate-limit error, surface a clearer message
            msg = str(e)
            lower = msg.lower()
            if "quota" in lower or "limit" in lower or "rate" in lower or "exhausted" in lower:
                raise RuntimeError(f"Gemini quota/rate error: {msg}")

            # Otherwise fallback to non-streaming result to preserve UX
            result = await self.generate(prompt, actual, max_tokens, temperature)
            yield result["content"]
            return

        async for chunk in stream:
            text = self._extract_text(chunk)
            if text:
                yield text

    # -----------------------------------------------------
    # Token Counter Passthrough
    # -----------------------------------------------------
    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "gemini")

    # -----------------------------------------------------
    # Cost Estimation (required by BaseLLMProvider)
    # -----------------------------------------------------
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        """
        Gemini pricing (per 1K tokens):
        Flash:  $0.075 input / $0.30 output
        Pro:    $1.25 input / $5.00 output
        """
        model = model or self.default_model
        model_lower = model.lower()

        if "flash" in model_lower:
            input_rate = 0.075 / 1000
            output_rate = 0.30 / 1000
        else:
            input_rate = 1.25 / 1000
            output_rate = 5.00 / 1000

        input_cost = prompt_tokens * input_rate
        output_cost = completion_tokens * output_rate

        return input_cost + output_cost



================================================
FILE: app/llm/mock.py
================================================
from .base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Simple mock LLM provider for testing without external APIs."""

    def generate(self, prompt: str, model: str = "mock") -> tuple[str, int]:
        # Very simple echo response and token counting
        response = f"Mock response: {prompt}"
        tokens = self.count_tokens(response)
        return response, tokens

    def count_tokens(self, text: str) -> int:
        # Naive token counting: whitespace-separated words
        return max(1, len(text.split()))

    def estimate_cost(self, tokens: int) -> float:
        # Fake cost model
        return tokens * 0.0001



================================================
FILE: app/llm/openai_provider.py
================================================
from typing import Optional, AsyncIterator
import os
import asyncio

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.utils.stream_emulation import emulate_stream_text

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider with basic async support"""

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if AsyncOpenAI is not None else None
        self.provider_name = "openai"

    async def generate(self,
                      prompt: str,
                      model: str = "gpt-3.5-turbo",
                      max_tokens: int = 1000,
                      temperature: float = 0.7) -> dict:
        if self.client is None:
            raise Exception("OpenAI client not available (library not installed)")
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "model": getattr(response, "model", model),
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def stream_generate(self, prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1000, temperature: float = 0.7) -> AsyncIterator[str]:
        if self.client is None:
            raise Exception("OpenAI client not available (library not installed)")
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    yield delta.content
        except Exception:
            # Streaming not available or failed — fallback to non-streaming generate
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content', '') if isinstance(result, dict) else str(result)
                # Emulate streaming by chunking the final content
                async for part in emulate_stream_text(content):
                    yield part
            except Exception:
                # swallow errors to avoid crashing the SSE handler
                return

    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "openai")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        prices = {
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        }
        pricing = prices.get(model, prices["gpt-3.5-turbo"])
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return input_cost + output_cost



================================================
FILE: app/routers/__init__.py
================================================
"""Routers package"""

__all__ = ["users", "subscriptions", "chat", "admin"]



================================================
FILE: app/routers/admin.py
================================================
from fastapi import APIRouter, HTTPException
from .. import models
from ..dependencies import get_user_cost_summary, get_user_or_404, get_subscription_or_404_by_user, get_real_api_usage_summary

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/costs/{user_id}")
async def get_user_cost_report(user_id: str):
    """Get API cost report for a specific user"""
    user = get_user_or_404(user_id)
    cost_summary = get_user_cost_summary(user_id)
    
    subscription = get_subscription_or_404_by_user(user_id)
    
    return {
        "user": {"id": user["id"], "email": user["email"], "usernamae": user["username"]},
        "subscription": {
            "tier": subscription["tier_name"],
            "monthly_cost_usd": subscription["monthly_cost_usd"],
            "monthly_api_cost_usd": subscription["monthly_api_cost_usd"],
        },
        "usage": cost_summary,
    }


@router.get("/costs")
async def get_all_costs():
    """Get cost report for all users (admin only)"""
    total_by_provider = {}
    user_summaries = []
    
    for user_id in models.users_db.keys():
        try:
            cost_summary = get_user_cost_summary(user_id)
            user_summaries.append({
                "user_id": user_id,
                **cost_summary
            })
            
            for provider, breakdown in cost_summary["breakdown_by_provider"].items():
                if provider not in total_by_provider:
                    total_by_provider[provider] = {"calls": 0, "tokens": 0, "cost": 0.0}
                total_by_provider[provider]["calls"] += breakdown["calls"]
                total_by_provider[provider]["tokens"] += breakdown["tokens"]
                total_by_provider[provider]["cost"] += breakdown["cost"]
        except Exception:
            pass
    
    return {
        "total_users": len(models.users_db),
        "total_by_provider": total_by_provider,
        "users": user_summaries,
    }


@router.get("/subscriptions")
async def list_all_subscriptions():
    """List all user subscriptions (admin only)"""
    subs = []
    for sub in models.subscriptions_db.values():
        subs.append({
            "user_id": sub["user_id"],
            "tier": sub["tier_name"],
            "tokens_limit": sub["tokens_limit"],
            "tokens_used": sub["tokens_used"],
            "tokens_remaining": sub["tokens_remaining"],
            "credits_limit": sub.get("credits_limit"),
            "credits_used": sub.get("credits_used"),
            "credits_remaining": sub.get("credits_remaining"),
            "status": sub["status"],
            "monthly_cost_usd": sub["monthly_cost_usd"],
            "monthly_api_cost_usd": sub["monthly_api_cost_usd"],
        })
    return subs


@router.get("/tier-breakdown")
async def get_tier_breakdown():
    """See how many users per tier"""
    breakdown = {}
    for sub in models.subscriptions_db.values():
        tier = sub["tier_name"]
        if tier not in breakdown:
            breakdown[tier] = {"count": 0, "users": []}
        breakdown[tier]["count"] += 1
        breakdown[tier]["users"].append(sub["user_id"])
    return breakdown


@router.get("/usage/{user_id}")
async def get_user_real_api_usage(user_id: str):
    """Get real API usage for a specific user (actual API calls made)"""
    user = get_user_or_404(user_id)
    usage = get_real_api_usage_summary(user_id)
    
    return {
        "user": {"id": user["id"], "email": user["email"], "username": user["username"]},
        "real_api_usage": usage,
    }


@router.get("/usage")
async def get_all_real_api_usage():
    """Get real API usage across all users and providers"""
    total_by_provider = {
        "gemini": {"calls": 0, "tokens": 0, "cost": 0.0},
        "openai": {"calls": 0, "tokens": 0, "cost": 0.0},
        "anthropic": {"calls": 0, "tokens": 0, "cost": 0.0},
    }
    
    user_summaries = []
    
    for user_id in models.users_db.keys():
        try:
            usage = get_real_api_usage_summary(user_id)
            user_summaries.append({
                "user_id": user_id,
                **usage
            })
            
            # Aggregate by provider
            for provider, provider_data in usage.get("by_provider", {}).items():
                if provider in total_by_provider:
                    total_by_provider[provider]["calls"] += provider_data["calls"]
                    total_by_provider[provider]["tokens"] += provider_data["total_tokens"]
                    total_by_provider[provider]["cost"] += provider_data["cost_usd"]
        except Exception:
            pass
    
    return {
        "total_users_with_usage": len(user_summaries),
        "total_api_calls_made": sum(u["total_api_calls"] for u in user_summaries),
        "total_tokens_consumed": sum(u["total_tokens"] for u in user_summaries),
        "total_cost_usd": round(sum(u["total_cost_usd"] for u in user_summaries), 4),
        "by_provider": {k: {**v, "cost": round(v["cost"], 4)} for k, v in total_by_provider.items()},
        "users": user_summaries,
    }


@router.get("/usage/provider/{provider}")
async def get_provider_usage(provider: str):
    """Get usage statistics for a specific provider (gemini, openai, anthropic)"""
    provider_lower = provider.lower()
    total_calls = 0
    total_tokens = 0
    total_cost = 0.0
    user_data = []
    
    for user_id, user_usage_dict in models.api_usage_db.items():
        if provider_lower in user_usage_dict:
            data = user_usage_dict[provider_lower]
            total_calls += data["calls"]
            total_tokens += data["total_tokens"]
            total_cost += data["cost_usd"]
            user_data.append({
                "user_id": user_id,
                "calls": data["calls"],
                "tokens": data["total_tokens"],
                "cost_usd": round(data["cost_usd"], 4),
                "models_used": list(data["models_used"]),
                "last_used": data["last_used"].isoformat() if data["last_used"] else None,
            })
    
    return {
        "provider": provider_lower,
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "users_count": len(user_data),
        "users": user_data,
    }



================================================
FILE: app/routers/chat.py
================================================
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
import os
from datetime import datetime
import uuid
from collections import defaultdict
import time

from .. import schemas, models
from ..llm.factory import llm_factory
from ..dependencies import (
    conversations_db,
    messages_db,
    get_user_or_404,
    get_subscription_or_404_by_user,
    check_subscription_active,
    check_model_access,
    check_tokens_available,
    deduct_tokens,
    check_credits_available,
    deduct_credits,
    track_api_cost,
    track_real_api_usage,
    check_rate_limit,
)
from ..utils.stream_emulation import emulate_stream_text

router = APIRouter(prefix="", tags=["Chat"])

# Simple per-user spacing tracker to avoid provider free-tier rate limits (seconds)
user_last_request = defaultdict(float)


@router.post("/chat/", response_model=schemas.ChatResponse)
async def chat(request: schemas.ChatRequest, user_id: str = Header(None)):
    """Chat endpoint with real LLMs and subscription management"""
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user-id header")

    # Check user exists
    user = get_user_or_404(user_id)
    
    # Get subscription and validate
    subscription = get_subscription_or_404_by_user(user_id)
    check_subscription_active(subscription)
    
    model = request.model or "mock"
    
    # Check model access
    check_model_access(subscription, model)
    
    # Check rate limit
    check_rate_limit(user_id, subscription["rate_limit_per_minute"])
    
    # Create provider
    provider = llm_factory.create_provider(model)
    
    # Estimate tokens and check credits
    estimated = provider.count_tokens(request.prompt)
    # Use credits-based check (conservative: include requested max_tokens)
    check_credits_available(subscription, estimated + (request.max_tokens or 1000), model)
    
    try:
        # Call LLM
        result = await provider.generate(
            prompt=request.prompt,
            model=model,
            max_tokens=request.max_tokens or 1000,
            temperature=request.temperature or 0.7,
        )

        # Extract result data
        content = result.get("content") if isinstance(result, dict) else str(result)
        model_used = result.get("model", model) if isinstance(result, dict) else model
        prompt_tokens = result.get("prompt_tokens", 0) if isinstance(result, dict) else 0
        completion_tokens = result.get("completion_tokens", 0) if isinstance(result, dict) else 0
        total_tokens = result.get("total_tokens", prompt_tokens + completion_tokens) if isinstance(result, dict) else (prompt_tokens + completion_tokens)

        # Deduct credits based on model multiplier
        credits_deducted = deduct_credits(subscription, total_tokens, model_used)
        
        # Track API cost (provider calculates cost based on tokens)
        cost = provider.estimate_cost(prompt_tokens, completion_tokens, model_used)
        track_api_cost(user_id, provider.provider_name, model_used, prompt_tokens, completion_tokens, cost)
        
        # Track real API usage
        track_real_api_usage(user_id, provider.provider_name, model_used, prompt_tokens, completion_tokens, cost)
        
        # Save conversation/message
        conv_id = request.conversation_id or str(uuid.uuid4())
        if conv_id not in conversations_db:
            conversations_db[conv_id] = {"id": conv_id, "user_id": user_id, "created_at": datetime.now()}

        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "conversation_id": conv_id,
            "role": "assistant",
            "content": content,
            "model": model_used,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "api_cost_usd": round(cost, 4),
            "created_at": datetime.now(),
        }
        messages_db[message_id] = message

        return schemas.ChatResponse(
            message_id=message_id,
            conversation_id=conv_id,
            content=content,
            model=model_used,
            tokens_used=total_tokens,
            tokens_remaining=subscription.get("tokens_remaining"),
            # New credit fields for client-side visibility
            **{"credits_used": subscription.get("credits_used"), "credits_remaining": subscription.get("credits_remaining")}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/models/formatted")
async def list_models_formatted():
    """
    Returns models in a flat format that the frontend expects.
    Each model includes: value, label, provider, tier
    
    Example response:
    [
        {
            "value": "gpt-4",
            "label": "GPT-4",
            "provider": "openai",
            "tier": "enterprise"
        },
        ...
    ]
    """
    from .. import models as app_models
    
    # Get raw models from factory
    raw_models = llm_factory.get_available_models()
    
    # Model tier mapping (which tier can access which models)
    model_tier_map = {}
    for tier_name, tier_info in app_models.SUBSCRIPTION_TIERS.items():
        for model in tier_info["allowed_models"]:
            if model not in model_tier_map:
                model_tier_map[model] = tier_name
    
    # Flatten the nested provider structure
    formatted_models = []
    
    for provider, model_list in raw_models.items():
        for model_id in model_list:
            # Determine tier (default to "pro" if not found)
            tier = model_tier_map.get(model_id, "pro")
            
            # Create a human-readable label
            label = model_id.replace("-", " ").title()
            
            # Special case formatting for common models
            if "gpt" in model_id.lower():
                label = model_id.upper().replace("-", " ")
            elif "claude" in model_id.lower():
                label = "Claude " + model_id.split("-")[1].capitalize()
            elif "gemini" in model_id.lower():
                parts = model_id.split("-")
                if len(parts) >= 2:
                    label = f"Gemini {parts[1].capitalize()}"
                    if len(parts) >= 3:
                        label += f" {parts[2].capitalize()}"
            
            formatted_models.append({
                "value": model_id,
                "label": label,
                "provider": provider,
                "tier": tier
            })
    
    return formatted_models


@router.get("/conversations/")
async def list_conversations():
    return list(conversations_db.values())


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    msgs = [m for m in messages_db.values() if m["conversation_id"] == conversation_id]
    return msgs


@router.get("/chat/models")
async def list_models():
    return llm_factory.get_available_models()


@router.post("/stream/chat")
async def stream_chat(request: Request):
    """HTTP SSE streaming endpoint.

    The client POSTs a JSON body with the same fields as the websocket protocol:
      {"prompt":"...","model":"...","conversation_id":"...","user_id":"...","max_tokens":N}

    The server responds with `text/event-stream` SSE events where each event's `data` is a JSON payload:
      data: {"type":"chunk","content":"..."}
      data: {"type":"done","message_id":"...","tokens_used":N,...}
      data: {"type":"error","error":"code","message":"..."}
    """
    try:
        data = await request.json()
    except Exception:
        return StreamingResponse(("""data: {"type":"error","error":"invalid_request","message":"Expected JSON body"}\n\n"""), media_type="text/event-stream")

    # Validate input
    if not isinstance(data, dict):
        return StreamingResponse(("""data: {"type":"error","error":"invalid_request","message":"Expected JSON object"}\n\n"""), media_type="text/event-stream")

    prompt = data.get("prompt")
    model = data.get("model", "mock")
    user_id = data.get("user_id")
    conversation_id = data.get("conversation_id")
    max_tokens = data.get("max_tokens", 1000)
    temperature = data.get("temperature", 0.7)

    if not user_id:
        return StreamingResponse(("""data: {"type":"error","error":"missing_user","message":"user_id is required"}\n\n"""), media_type="text/event-stream")

    # Validate user and subscription
    try:
        user = get_user_or_404(user_id)
        subscription = get_subscription_or_404_by_user(user_id)
        check_subscription_active(subscription)
    except HTTPException as e:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"invalid_user_or_subscription\", \"message\": \"{str(e.detail)}\"}}\n\n"), media_type="text/event-stream")

    # Check model access
    try:
        check_model_access(subscription, model)
    except HTTPException as e:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"model_not_allowed\", \"message\": \"{str(e.detail)}\"}}\n\n"), media_type="text/event-stream")

    # Per-user spacing
    try:
        now = time.time()
        last = user_last_request.get(user_id, 0.0)
        min_spacing = 4.0
        if now - last < min_spacing:
            wait = int(min_spacing - (now - last))
            return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"rate_limit\", \"message\": \"Please wait {wait} seconds between requests (provider rate limit)\"}}\n\n"), media_type="text/event-stream")
        user_last_request[user_id] = now
    except Exception:
        pass

    # Rate limit check
    try:
        check_rate_limit(user_id, subscription["rate_limit_per_minute"])
    except HTTPException as e:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"rate_limited\", \"message\": \"{str(e.detail)}\"}}\n\n"), media_type="text/event-stream")

    provider = llm_factory.create_provider(model)

    # Estimate tokens conservatively
    try:
        estimated = provider.count_tokens(prompt)
    except Exception:
        estimated = len(prompt.split())

    # Check credits instead of raw tokens
    try:
        check_credits_available(subscription, estimated + max_tokens, model)
    except Exception:
        return StreamingResponse((f"data: {{\"type\": \"error\", \"error\": \"insufficient_credits\", \"message\": \"Need ~{int((estimated + max_tokens) * 1)} credits (est), but only {subscription.get('credits_remaining')} remaining\"}}\n\n"), media_type="text/event-stream")

    import json

    async def event_stream():
        full_response = ""
        any_chunk_sent = False

        try:
            async for chunk in provider.stream_generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature):
                chunk_text = chunk if isinstance(chunk, str) else str(chunk)
                # Skip empty/whitespace-only chunks to avoid noisy empty SSE events
                if not chunk_text or chunk_text.strip() == "":
                    continue

                # SSE event: data: <json>\n\n
                payload = json.dumps({"type": "chunk", "content": chunk_text})
                yield f"data: {payload}\n\n"
                full_response += chunk_text
                any_chunk_sent = True

        except Exception as e:
            # If this looks like a quota or rate-limit error, surface a clearer message and stop
            try:
                msg = str(e)
                lower = msg.lower()
            except Exception:
                lower = ""

            if "quota" in lower or "limit" in lower or "rate" in lower or "exhausted" in lower:
                try:
                    payload = json.dumps({"type": "error", "error": "llm_error", "message": msg})
                    yield f"data: {payload}\n\n"
                except Exception:
                    pass
                return

            # For other errors, attempt a non-streaming fallback so clients still get an answer
            try:
                result = await provider.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content') if isinstance(result, dict) else str(result)
                # If we have content, emulate streaming it
                if content:
                    async for part in emulate_stream_text(content):
                        if not part or part.strip() == "":
                            continue
                        payload = json.dumps({"type": "chunk", "content": part})
                        yield f"data: {payload}\n\n"
                        full_response += part
                        any_chunk_sent = True
                else:
                    # no content from generate - fall through to finalization which will send done/error
                    pass
            except Exception:
                # if fallback also fails, send an error and stop
                try:
                    payload = json.dumps({"type": "error", "error": "llm_error", "message": str(e)})
                    yield f"data: {payload}\n\n"
                except Exception:
                    pass
                return

        # If provider produced no chunks (silent stream), try non-streaming generate and emulate
        if not any_chunk_sent:
            try:
                # Attempt to fetch the final content non-streaming and stream it to client
                result = await provider.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content') if isinstance(result, dict) else str(result)
                if content:
                    emulated_sent = False
                    async for part in emulate_stream_text(content):
                        if not part or part.strip() == "":
                            continue
                        payload = json.dumps({"type": "chunk", "content": part})
                        yield f"data: {payload}\n\n"
                        full_response += part
                        any_chunk_sent = True
                        emulated_sent = True

                    # If emulation produced nothing (very short content), send the full content as one chunk
                    if not emulated_sent and content:
                        payload = json.dumps({"type": "chunk", "content": content})
                        yield f"data: {payload}\n\n"
                        full_response += content
                        any_chunk_sent = True
                else:
                    # no content from generate - fall through to finalization which will send done/error
                    pass
            except Exception:
                # If this fails, continue to finalization to send done/error
                pass

        # After streaming completes, compute tokens and update subscription
        try:
            prompt_tokens = provider.count_tokens(prompt)
            completion_tokens = provider.count_tokens(full_response)
            total_tokens = prompt_tokens + completion_tokens

            # Deduct credits (based on model multiplier)
            credits = deduct_credits(subscription, total_tokens, model)

            cost = provider.estimate_cost(prompt_tokens, completion_tokens, model) if hasattr(provider, 'estimate_cost') else 0.0
            track_api_cost(user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)
            track_real_api_usage(user_id, provider.provider_name, model, prompt_tokens, completion_tokens, cost)

            conv_id = conversation_id or str(uuid.uuid4())
            if conv_id not in conversations_db:
                conversations_db[conv_id] = {"id": conv_id, "user_id": user_id, "created_at": datetime.now()}

            message_id = str(uuid.uuid4())
            message = {
                "id": message_id,
                "conversation_id": conv_id,
                "role": "assistant",
                "content": full_response,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "api_cost_usd": round(cost, 6),
                "created_at": datetime.now(),
            }
            messages_db[message_id] = message

            payload = json.dumps({"type": "done", "message_id": message_id, "tokens_used": total_tokens, "tokens_remaining": subscription.get("tokens_remaining"), "model": model, "credits_used": subscription.get("credits_used"), "credits_remaining": subscription.get("credits_remaining")})
            yield f"data: {payload}\n\n"

        except Exception as e:
            try:
                payload = json.dumps({"type": "error", "error": "server_error", "message": str(e)})
                yield f"data: {payload}\n\n"
            except Exception:
                pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")




================================================
FILE: app/routers/subscriptions.py
================================================
from fastapi import APIRouter, HTTPException
from datetime import datetime

from .. import schemas, models
from ..dependencies import get_user_or_404, get_subscription_or_404_by_user

router = APIRouter(prefix="", tags=["Subscriptions"])


@router.get("/subscriptions/{user_id}", response_model=schemas.SubscriptionDetail)
async def get_user_subscription(user_id: str):
    """Get subscription details for a user"""
    user = get_user_or_404(user_id)
    subscription = get_subscription_or_404_by_user(user_id)
    
    return schemas.SubscriptionDetail(
        id=subscription["id"],
        user_id=subscription["user_id"],
        tier_id=subscription["tier_id"],
        tier_name=subscription["tier_name"],
        allowed_models=subscription["allowed_models"],
        tokens_limit=subscription["tokens_limit"],
        tokens_used=subscription["tokens_used"],
        tokens_remaining=subscription["tokens_remaining"],
        credits_limit=subscription.get("credits_limit"),
        credits_used=subscription.get("credits_used"),
        credits_remaining=subscription.get("credits_remaining"),
        monthly_cost_usd=subscription["monthly_cost_usd"],
        monthly_api_cost_usd=subscription["monthly_api_cost_usd"],
        requests_this_minute=0,  # TODO: implement rate limiter tracking
        status=subscription["status"],
        created_at=subscription["created_at"],
        expires_at=subscription.get("expires_at"),
    )


@router.post("/subscriptions/{user_id}/upgrade", response_model=schemas.SubscriptionDetail)
async def upgrade_subscription(user_id: str, tier: str = "pro"):
    """Upgrade user to a different tier (free, pro, enterprise)"""
    user = get_user_or_404(user_id)
    if tier not in models.SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}. Available: {list(models.SUBSCRIPTION_TIERS.keys())}")
    
    # Find existing subscription
    old_sub = get_subscription_or_404_by_user(user_id)
    
    # Delete old and create new
    del models.subscriptions_db[old_sub["id"]]
    new_sub = models.create_default_subscription(user_id, tier)
    
    return schemas.SubscriptionDetail(
        id=new_sub["id"],
        user_id=new_sub["user_id"],
        tier_id=new_sub["tier_id"],
        tier_name=new_sub["tier_name"],
        allowed_models=new_sub["allowed_models"],
        tokens_limit=new_sub["tokens_limit"],
        tokens_used=new_sub["tokens_used"],
        tokens_remaining=new_sub["tokens_remaining"],
        credits_limit=new_sub.get("credits_limit"),
        credits_used=new_sub.get("credits_used"),
        credits_remaining=new_sub.get("credits_remaining"),
        monthly_cost_usd=new_sub["monthly_cost_usd"],
        monthly_api_cost_usd=new_sub["monthly_api_cost_usd"],
        requests_this_minute=0,
        status=new_sub["status"],
        created_at=new_sub["created_at"],
        expires_at=new_sub.get("expires_at"),
    )


@router.post("/subscriptions/{user_id}/add-tokens")
async def add_tokens(user_id: str, tokens: int):
    """Grant additional tokens to a user (admin action)"""
    if tokens <= 0:
        raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    user = get_user_or_404(user_id)
    subscription = get_subscription_or_404_by_user(user_id)
    
    subscription["tokens_remaining"] += tokens
    subscription["tokens_limit"] += tokens
    
    return {
        "message": f"Added {tokens} tokens to user",
        "tokens_remaining": subscription["tokens_remaining"],
        "tokens_limit": subscription["tokens_limit"],
    }


@router.post("/subscriptions/{user_id}/add-credits")
async def add_credits(user_id: str, credits: int):
    """Grant additional credits to a user (admin action)"""
    if credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    user = get_user_or_404(user_id)
    subscription = get_subscription_or_404_by_user(user_id)

    subscription["credits_remaining"] = subscription.get("credits_remaining", 0) + credits
    subscription["credits_limit"] = subscription.get("credits_limit", 0) + credits

    return {
        "message": f"Added {credits} credits to user",
        "credits_remaining": subscription["credits_remaining"],
        "credits_limit": subscription["credits_limit"],
    }


@router.put("/subscriptions/{user_id}/use-tokens", response_model=schemas.TokenUsageResponse)
async def use_tokens(user_id: str, tokens: int):
    """Deduct tokens from a user's subscription"""
    if tokens <= 0:
        raise HTTPException(status_code=400, detail="Tokens must be positive")
    
    user = get_user_or_404(user_id)
    subscription = get_subscription_or_404_by_user(user_id)
    
    if subscription["tokens_remaining"] < tokens:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient tokens. Required: {tokens}, Available: {subscription['tokens_remaining']}",
        )
    
    subscription["tokens_used"] += tokens
    subscription["tokens_remaining"] -= tokens
    
    percentage_used = (subscription["tokens_used"] / subscription["tokens_limit"]) * 100
    
    return schemas.TokenUsageResponse(
        tokens_used=subscription["tokens_used"],
        tokens_remaining=subscription["tokens_remaining"],
        tokens_limit=subscription["tokens_limit"],
        percentage_used=round(percentage_used, 2),
    )


@router.put("/subscriptions/{user_id}/use-credits", response_model=schemas.TokenUsageResponse)
async def use_credits(user_id: str, credits: int):
    """Deduct credits from a user's subscription (admin/test action)"""
    if credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    user = get_user_or_404(user_id)
    subscription = get_subscription_or_404_by_user(user_id)

    if subscription.get("credits_remaining", 0) < credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {credits}, Available: {subscription.get('credits_remaining', 0)}",
        )

    subscription["credits_used"] = subscription.get("credits_used", 0) + credits
    subscription["credits_remaining"] = subscription.get("credits_remaining", 0) - credits

    # Reuse TokenUsageResponse schema for simplicity (it now includes credits)
    percentage_used = 0.0
    if subscription.get("credits_limit"):
        percentage_used = (subscription.get("credits_used", 0) / subscription.get("credits_limit")) * 100

    return schemas.TokenUsageResponse(
        tokens_used=subscription.get("credits_used", 0),
        tokens_remaining=subscription.get("credits_remaining", 0),
        tokens_limit=subscription.get("credits_limit", 0),
        percentage_used=round(percentage_used, 2),
    )


@router.get("/subscriptions/")
async def list_available_tiers():
    """List all available subscription tiers"""
    return {
        tier_name: {
            "tier_id": tier["tier_id"],
            "name": tier["name"],
            "allowed_models": tier["allowed_models"],
            "tokens_per_month": tier["tokens_per_month"],
            "rate_limit_per_minute": tier["rate_limit_per_minute"],
            "cost_usd": tier["cost_usd"],
        }
        for tier_name, tier in models.SUBSCRIPTION_TIERS.items()
    }




================================================
FILE: app/routers/users.py
================================================
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid

from .. import schemas, models

router = APIRouter(prefix="", tags=["Users"])


@router.post("/users/", response_model=schemas.UserResponse, status_code=201)
async def create_user(user: schemas.UserCreate):
    # Check for existing email or username
    for existing_user in models.users_db.values():
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        if existing_user["username"] == user.username:
            raise HTTPException(status_code=400, detail="Username already taken")

    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "email": user.email,
        "username": user.username,
        "hashed_password": f"hashed_{user.password}",
        "is_active": True,
        "created_at": datetime.now(),
    }
    models.users_db[user_id] = new_user
    models.create_default_subscription(user_id, "free")
    return schemas.UserResponse(**new_user)


@router.get("/users/", response_model=list[schemas.UserResponse])
async def list_users():
    return [schemas.UserResponse(**u) for u in models.users_db.values()]


@router.get("/users/{user_id}", response_model=schemas.UserResponse)
async def get_user(user_id: str):
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return schemas.UserResponse(**models.users_db[user_id])


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str):
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")
    # delete subscriptions
    subs = [sid for sid, s in models.subscriptions_db.items() if s["user_id"] == user_id]
    for sid in subs:
        del models.subscriptions_db[sid]
    del models.users_db[user_id]
    return None


@router.get("/users/{user_id}/tokens", response_model=schemas.TokenUsageResponse)
async def get_user_tokens(user_id: str):
    if user_id not in models.users_db:
        raise HTTPException(status_code=404, detail="User not found")

    user_subscription = None
    for sub in models.subscriptions_db.values():
        if sub["user_id"] == user_id:
            user_subscription = sub
            break

    if not user_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    percentage_used = (user_subscription["tokens_used"] / user_subscription["tokens_limit"]) * 100

    return schemas.TokenUsageResponse(
        tokens_used=user_subscription["tokens_used"],
        tokens_remaining=user_subscription["tokens_remaining"],
        tokens_limit=user_subscription["tokens_limit"],
        percentage_used=round(percentage_used, 2),
    )



================================================
FILE: app/utils/stream_emulation.py
================================================
import asyncio
from typing import AsyncIterator

async def emulate_stream_text(text: str, chunk_size: int = 120, delay: float = 0.02) -> AsyncIterator[str]:
    """Asynchronously yield `text` in chunks with a small delay between them.

    - `chunk_size`: number of characters per emitted chunk.
    - `delay`: seconds to await between chunks (can be 0 for immediate emission).

    Use this when a provider does not support streaming; it provides a smooth, client-friendly streamed experience.
    """
    if not text:
        return
    pos = 0
    L = len(text)
    while pos < L:
        end = min(pos + chunk_size, L)
        yield text[pos:end]
        pos = end
        if pos < L:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return



================================================
FILE: app/utils/token_counter.py
================================================
"""Token counting utilities for different LLM providers"""
from typing import Literal, List
try:
    import tiktoken
except Exception:
    tiktoken = None

ProviderType = Literal["openai", "anthropic", "gemini"]


class TokenCounter:
    """Count tokens for different LLM providers"""

    def __init__(self):
        # OpenAI uses tiktoken if available
        self.openai_encoding = None
        if tiktoken is not None:
            try:
                self.openai_encoding = tiktoken.encoding_for_model("gpt-4")
            except Exception:
                self.openai_encoding = None

    def count_tokens(self, text: str, provider: ProviderType) -> int:
        if provider == "openai":
            if self.openai_encoding is not None:
                try:
                    return len(self.openai_encoding.encode(text))
                except Exception:
                    pass
            # fallback approximate
            return max(1, len(text.split()))

        elif provider == "anthropic":
            # Anthropic approximate: use same as openai if available
            if self.openai_encoding is not None:
                try:
                    return len(self.openai_encoding.encode(text))
                except Exception:
                    pass
            return max(1, len(text.split()))

        elif provider == "gemini":
            # Gemini: approximate as 1 token ≈ 4 chars
            return max(1, len(text) // 4)

        else:
            return max(1, len(text) // 4)

    def estimate_tokens(self, prompt: str, provider: ProviderType,
                        max_completion_tokens: int = 1000) -> dict:
        prompt_tokens = self.count_tokens(prompt, provider)
        return {
            "prompt_tokens": prompt_tokens,
            "max_completion_tokens": max_completion_tokens,
            "estimated_total": prompt_tokens + max_completion_tokens,
        }


# Global instance
token_counter = TokenCounter()



================================================
FILE: components/chat-message.tsx
================================================
import type { Message } from "@/lib/api"
import { Sparkles } from "lucide-react"

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"} mb-6 animate-in fade-in slide-in-from-bottom-2 duration-300`}
    >
      <div className={`flex gap-3 max-w-2xl ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center flex-shrink-0 mt-1">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        )}

        <div
          className={`rounded-xl px-4 py-3 ${
            isUser
              ? "bg-primary text-primary-foreground rounded-br-none"
              : "bg-muted text-muted-foreground rounded-bl-none"
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
            {isStreaming && <span className="animate-pulse">▌</span>}
          </p>

          {!isUser && message.model && (
            <div className="text-xs opacity-60 mt-2 pt-2 border-t border-current/20">
              <p>{message.model}</p>
              {message.tokens_used && <p>Tokens: {message.tokens_used}</p>}
              {message.credits_used && <p>Credits: {message.credits_used}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}




================================================
FILE: components/model-selector.tsx
================================================
"use client"

import { useState, useEffect } from "react"
import type { Model } from "@/lib/api"
import { getAvailableModels } from "@/lib/api"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Sparkles } from "lucide-react"

interface ModelSelectorProps {
  value: string
  onChange: (model: string) => void
  userTier?: string
}

export function ModelSelector({ value, onChange, userTier = "free" }: ModelSelectorProps) {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getAvailableModels()
        setModels(data)
        if (data.length > 0 && !value) {
          onChange(data[0].value)
        }
      } catch (err) {
        console.error("Failed to fetch models:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchModels()
  }, [])

  const groupedModels = models.reduce(
    (acc, model) => {
      const provider = model.provider
      if (!acc[provider]) acc[provider] = []
      acc[provider].push(model)
      return acc
    },
    {} as Record<string, Model[]>,
  )

  if (loading) {
    return <div className="h-10 bg-muted rounded-lg animate-pulse" />
  }

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-full md:w-64 gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent className="max-h-64">
        {Object.entries(groupedModels).map(([provider, providerModels]) => (
          <div key={provider}>
            <div className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {provider}
            </div>
            {providerModels.map((model) => (
              <SelectItem key={model.value} value={model.value} disabled={userTier === "free" && model.tier !== "free"}>
                <div className="flex items-center gap-2">
                  {model.label}
                  {model.tier !== "free" && (
                    <Badge variant="outline" className="text-xs">
                      {model.tier}
                    </Badge>
                  )}
                </div>
              </SelectItem>
            ))}
          </div>
        ))}
      </SelectContent>
    </Select>
  )
}




================================================
FILE: components/sidebar.tsx
================================================
"use client"

import Link from "next/link"
import { Plus, MessageCircle, Users, Gamepad2, Settings } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SidebarProps {
  onNewChat: () => void
}

export function Sidebar({ onNewChat }: SidebarProps) {
  return (
    <div className="w-64 h-screen bg-sidebar border-r border-sidebar-border flex flex-col p-4 overflow-hidden">
      {/* Logo */}
      <div className="flex items-center gap-2 mb-8">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <span className="text-white font-bold text-lg">🎉</span>
        </div>
        <span className="font-bold text-lg">AI Fiesta</span>
      </div>

      {/* New Chat */}
      <Button onClick={onNewChat} variant="outline" className="w-full justify-start gap-2 mb-8 bg-transparent">
        <Plus className="w-4 h-4" />
        New chat
      </Button>

      {/* Navigation */}
      <nav className="space-y-2 flex-1">
        <Link href="/admin" className="block">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2 text-sidebar-foreground hover:bg-sidebar-accent"
          >
            <Users className="w-4 h-4" />
            Admin
          </Button>
        </Link>

        <button className="w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors flex items-center gap-2 text-sidebar-foreground">
          <MessageCircle className="w-4 h-4" />
          <span className="text-sm">Avatars</span>
        </button>

        <button className="w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors flex items-center gap-2 text-sidebar-foreground">
          <Gamepad2 className="w-4 h-4" />
          <span className="text-sm">Projects</span>
        </button>

        <button className="w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors flex items-center gap-2 text-sidebar-foreground">
          <Gamepad2 className="w-4 h-4" />
          <span className="text-sm">Games</span>
        </button>
      </nav>

      {/* History Section */}
      <div className="border-t border-sidebar-border pt-4 mb-4">
        <p className="text-xs uppercase tracking-wide text-sidebar-foreground/60 font-semibold mb-3">Yesterday</p>
        <button className="w-full text-left p-2 rounded hover:bg-sidebar-accent transition-colors text-sm text-sidebar-foreground">
          what is vercel
        </button>
      </div>

      {/* Footer */}
      <div className="border-t border-sidebar-border pt-4 space-y-3">
        <div className="bg-sidebar-accent rounded-lg p-3">
          <p className="font-semibold text-sm mb-2">Free Plan</p>
          <p className="text-xs text-sidebar-foreground/70 mb-2">2 / 3 messages used</p>
          <div className="w-full h-2 bg-sidebar-border rounded-full overflow-hidden">
            <div className="h-full w-2/3 bg-primary" />
          </div>
        </div>
        <Button variant="ghost" className="w-full justify-start gap-2 text-sidebar-foreground hover:bg-sidebar-accent">
          <Settings className="w-4 h-4" />
          Settings
        </Button>
      </div>
    </div>
  )
}




================================================
FILE: components/ui/badge.tsx
================================================
import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive transition-[color,box-shadow] overflow-hidden',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground [a&]:hover:bg-primary/90',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90',
        destructive:
          'border-transparent bg-destructive text-white [a&]:hover:bg-destructive/90 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/60',
        outline:
          'text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<'span'> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'span'

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }




================================================
FILE: components/ui/button.tsx
================================================
import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive:
          'bg-destructive text-white hover:bg-destructive/90 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/60',
        outline:
          'border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50',
        secondary:
          'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost:
          'hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2 has-[>svg]:px-3',
        sm: 'h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5',
        lg: 'h-10 rounded-md px-6 has-[>svg]:px-4',
        icon: 'size-9',
        'icon-sm': 'size-8',
        'icon-lg': 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }




================================================
FILE: components/ui/card.tsx
================================================
import * as React from 'react'

import { cn } from '@/lib/utils'

function Card({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card"
      className={cn(
        'bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm',
        className,
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        '@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6',
        className,
      )}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-title"
      className={cn('leading-none font-semibold', className)}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-description"
      className={cn('text-muted-foreground text-sm', className)}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        'col-start-2 row-span-2 row-start-1 self-start justify-self-end',
        className,
      )}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-content"
      className={cn('px-6', className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-footer"
      className={cn('flex items-center px-6 [.border-t]:pt-6', className)}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}




================================================
FILE: components/ui/input.tsx
================================================
import * as React from 'react'

import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground dark:bg-input/30 border-input h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
        'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]',
        'aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive',
        className,
      )}
      {...props}
    />
  )
}

export { Input }




================================================
FILE: components/ui/select.tsx
================================================
'use client'

import * as React from 'react'
import * as SelectPrimitive from '@radix-ui/react-select'
import { CheckIcon, ChevronDownIcon, ChevronUpIcon } from 'lucide-react'

import { cn } from '@/lib/utils'

function Select({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Root>) {
  return <SelectPrimitive.Root data-slot="select" {...props} />
}

function SelectGroup({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Group>) {
  return <SelectPrimitive.Group data-slot="select-group" {...props} />
}

function SelectValue({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Value>) {
  return <SelectPrimitive.Value data-slot="select-value" {...props} />
}

function SelectTrigger({
  className,
  size = 'default',
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Trigger> & {
  size?: 'sm' | 'default'
}) {
  return (
    <SelectPrimitive.Trigger
      data-slot="select-trigger"
      data-size={size}
      className={cn(
        "border-input data-[placeholder]:text-muted-foreground [&_svg:not([class*='text-'])]:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 dark:hover:bg-input/50 flex w-fit items-center justify-between gap-2 rounded-md border bg-transparent px-3 py-2 text-sm whitespace-nowrap shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 data-[size=default]:h-9 data-[size=sm]:h-8 *:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-2 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDownIcon className="size-4 opacity-50" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

function SelectContent({
  className,
  children,
  position = 'popper',
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        data-slot="select-content"
        className={cn(
          'bg-popover text-popover-foreground data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 relative z-50 max-h-(--radix-select-content-available-height) min-w-[8rem] origin-(--radix-select-content-transform-origin) overflow-x-hidden overflow-y-auto rounded-md border shadow-md',
          position === 'popper' &&
            'data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1',
          className,
        )}
        position={position}
        {...props}
      >
        <SelectScrollUpButton />
        <SelectPrimitive.Viewport
          className={cn(
            'p-1',
            position === 'popper' &&
              'h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)] scroll-my-1',
          )}
        >
          {children}
        </SelectPrimitive.Viewport>
        <SelectScrollDownButton />
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

function SelectLabel({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      data-slot="select-label"
      className={cn('text-muted-foreground px-2 py-1.5 text-xs', className)}
      {...props}
    />
  )
}

function SelectItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      data-slot="select-item"
      className={cn(
        "focus:bg-accent focus:text-accent-foreground [&_svg:not([class*='text-'])]:text-muted-foreground relative flex w-full cursor-default items-center gap-2 rounded-sm py-1.5 pr-8 pl-2 text-sm outline-hidden select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 *:[span]:last:flex *:[span]:last:items-center *:[span]:last:gap-2",
        className,
      )}
      {...props}
    >
      <span className="absolute right-2 flex size-3.5 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <CheckIcon className="size-4" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
}

function SelectSeparator({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Separator>) {
  return (
    <SelectPrimitive.Separator
      data-slot="select-separator"
      className={cn('bg-border pointer-events-none -mx-1 my-1 h-px', className)}
      {...props}
    />
  )
}

function SelectScrollUpButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollUpButton>) {
  return (
    <SelectPrimitive.ScrollUpButton
      data-slot="select-scroll-up-button"
      className={cn(
        'flex cursor-default items-center justify-center py-1',
        className,
      )}
      {...props}
    >
      <ChevronUpIcon className="size-4" />
    </SelectPrimitive.ScrollUpButton>
  )
}

function SelectScrollDownButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollDownButton>) {
  return (
    <SelectPrimitive.ScrollDownButton
      data-slot="select-scroll-down-button"
      className={cn(
        'flex cursor-default items-center justify-center py-1',
        className,
      )}
      {...props}
    >
      <ChevronDownIcon className="size-4" />
    </SelectPrimitive.ScrollDownButton>
  )
}

export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
}




================================================
FILE: components/ui/table.tsx
================================================
'use client'

import * as React from 'react'

import { cn } from '@/lib/utils'

function Table({ className, ...props }: React.ComponentProps<'table'>) {
  return (
    <div
      data-slot="table-container"
      className="relative w-full overflow-x-auto"
    >
      <table
        data-slot="table"
        className={cn('w-full caption-bottom text-sm', className)}
        {...props}
      />
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<'thead'>) {
  return (
    <thead
      data-slot="table-header"
      className={cn('[&_tr]:border-b', className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<'tbody'>) {
  return (
    <tbody
      data-slot="table-body"
      className={cn('[&_tr:last-child]:border-0', className)}
      {...props}
    />
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<'tfoot'>) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        'bg-muted/50 border-t font-medium [&>tr]:last:border-b-0',
        className,
      )}
      {...props}
    />
  )
}

function TableRow({ className, ...props }: React.ComponentProps<'tr'>) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        'hover:bg-muted/50 data-[state=selected]:bg-muted border-b transition-colors',
        className,
      )}
      {...props}
    />
  )
}

function TableHead({ className, ...props }: React.ComponentProps<'th'>) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        'text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]',
        className,
      )}
      {...props}
    />
  )
}

function TableCell({ className, ...props }: React.ComponentProps<'td'>) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        'p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]',
        className,
      )}
      {...props}
    />
  )
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<'caption'>) {
  return (
    <caption
      data-slot="table-caption"
      className={cn('text-muted-foreground mt-4 text-sm', className)}
      {...props}
    />
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}




================================================
FILE: docs/db_integration.md
================================================
# Database & ORM Integration Plan

This document outlines recommended design for integrating PostgreSQL and an async ORM into Fiesta for managing users, subscriptions, tokens, messages, and billing.

## Goals

- Provide durable storage for users, subscriptions, messages, and API usage
- Ensure atomic token deductions (no double-spend)
- Support migrations, connection pooling, and async access
- Be ready for scaling (multiple app workers, Redis for cross-worker coordination)

## Recommended Stack

- PostgreSQL (production)
- SQLAlchemy (1.4+) with async support + `asyncpg` driver OR `SQLModel` (Pydantic-style on top of SQLAlchemy)
- Alembic for migrations
- Redis (optional) for rate-limiting, presence, pub/sub across workers

## Core Tables / Models

- `users`:
  - id (PK, UUID)
  - email
  - username
  - hashed_password (nullable if using third-party auth)
  - created_at

- `subscriptions`:
  - id (PK, UUID)
  - user_id (FK -> users.id)
  - tier_id (free/pro/enterprise)
  - tokens_limit (int)
  - tokens_used (int)
  - tokens_remaining (int)
  - credits_limit (int)
  - credits_used (int)
  - credits_remaining (int)
  - monthly_api_cost_usd (float)
  - status (active/paused/cancelled)
  - created_at, expires_at

- `conversations`:
  - id (PK, UUID)
  - user_id (FK)
  - created_at

- `messages`:
  - id (PK, UUID)
  - conversation_id (FK)
  - user_id (FK)
  - role (user/assistant/system)
  - content (text)
  - model (text)
  - prompt_tokens (int)
  - completion_tokens (int)
  - total_tokens (int)
  - api_cost_usd (float)
  - created_at

- `api_usage` or `cost_tracker`:
  - id (PK, UUID)
  - user_id (FK)
  - provider (text)
  - model (text)
  - prompt_tokens (int)
  - completion_tokens (int)
  - total_tokens (int)
  - cost_usd (float)
  - created_at

## Atomic Token Deduction

To prevent race conditions when multiple concurrent requests attempt to deduct tokens:

1. Start a DB transaction (async session)
2. SELECT subscription row `FOR UPDATE` to lock it
3. Verify `tokens_remaining >= tokens_to_deduct`
4. Update `tokens_used` and `tokens_remaining`

If using credits, apply the same principle but compute `credits_to_deduct` using a deterministic multiplier per model (e.g. `credits = tokens * multiplier`). Verify `credits_remaining >= credits_to_deduct` inside the same transaction and update `credits_used`/`credits_remaining` atomically.
5. Commit transaction

If the transaction fails, return a 409-like error and retry logic on the client if appropriate.

## Migrations

- Use Alembic to manage schema changes
- Keep migration scripts in `alembic/` folder; run `alembic upgrade head` as part of deployment

## Scaling

- Use connection pooling (`asyncpg` + SQLAlchemy pooling) to handle concurrent DB connections
- Use Redis for rate limit counters and for cross-worker active-connection registry if you host multiple app workers

## Implementation Notes

- Start with `SQLModel` for quick wins; later migrate to full SQLAlchemy if you need complex relations/optimizations.
- Wrap DB writes for billing and analytics in background tasks if they are non-critical for the websocket response latency (but for token deduction do it synchronously in the transaction).

## Next Steps

- Add `requirements.txt` entries: `sqlmodel`, `asyncpg`, `alembic` (or `sqlalchemy` + `asyncpg` + `alembic`)
- Create initial migration with the core tables
- Implement `database.py` with `async_engine` and session helpers
- Replace in-memory stores with DB-backed models gradually



================================================
FILE: docs/streaming.md
================================================
# HTTP SSE Streaming - Design & Usage

This document explains the HTTP Server-Sent Events (SSE) streaming endpoint implemented in Fiesta and how to test it locally.

## Endpoint

- URL: `POST /stream/chat` (returns `text/event-stream` SSE)
- Purpose: Stream LLM responses chunk-by-chunk to clients in real-time over HTTP using SSE.

## Client → Server protocol (first message)

The client must POST a JSON body. Example:

```json
{
  "prompt": "Write a haiku about coding",
  "model": "gemini-2.5-pro",
  "conversation_id": "conv-123",
  "user_id": "demo-user-1",
  "max_tokens": 300
}
```

- `model`: model key (must be allowed by subscription). Use `gemini-2.5-pro` as the recommended default for Gemini. Availability depends on your key and region.
- `user_id`: server validates this against users stored in the system

## Server → Client messages

- Chunk messages (many):

```json
{ "type": "chunk", "content": "Once upon a time..." }
```

- Done message (single):

```json
{
  "type": "done",
  "message_id": "msg-...",
  "tokens_used": 25,
  "tokens_remaining": 975,
  "credits_used": 1,
  "credits_remaining": 499,
  "model": "gemini-2.5-flash"
}
```

- Error message (if something goes wrong):

```json
{ "type": "error", "error": "insufficient_tokens", "message": "You need 100 tokens but only have 50" }
```

## Token accounting policy (current)

- The server conservatively checks token availability before streaming, using `provider.count_tokens(prompt)` + `max_tokens`.
- Actual deduction happens after streaming completes and is based on actual produced tokens (prompt + completion).
- If the client disconnects before any chunk is sent, no tokens are deducted.
- If partial output was sent, actual produced tokens are deducted when the stream ends or when the server detects the disconnect (best-effort).

When using credits, follow the same conservative-check-before-stream approach but deduct credits after the stream completes using a model multiplier. The server returns `credits_used` and `credits_remaining` in the `done` event.

## Production considerations

- Move token accounting to a DB transaction and use `SELECT FOR UPDATE` to avoid race conditions.
- If you want to charge mid-stream, implement periodic interim commits (complex & error-prone).
- Use Redis for cross-worker presence and for rate-limiting.

## Testing locally

1. Ensure `.env` contains valid API keys (e.g. `GEMINI_API_KEY`).
2. Start the server:

```powershell
uvicorn main:app --reload
```

3. Open the test client in your browser:

- Visit `http://localhost:8000/test_client.html` (served by FastAPI)

4. Enter a prompt and click **Send (HTTP-SSE)**.

You should see content streamed in chunks and a final `done` message (SSE `data` events).

## Troubleshooting

- If `/test_client.html` returns an error, ensure the file exists in the project root.
- If streaming hangs: check server logs for LLM provider errors and ensure API keys are valid.

## Security

- Validate `user_id` and require authentication in production.
- Add rate-limiting and prompt length checks to prevent abuse.

## Feature flag

WebSockets were removed in favor of HTTP-SSE streaming. If you previously used the `ENABLE_WS_STREAMING` feature flag, it is no longer used.

### Gemini streaming note

- Gemini model availability and streaming support vary by key and region. Some Gemini models or keys do not support streaming (generateContent) even though they appear in `list_models()`.
- If the provider reports a streaming-related error (404 or unsupported), the app will automatically fall back to a non-streaming generate implementation for that request. The fallback behavior is logged and the client will receive a single `done` message with the final content instead of chunked `chunk` messages.

Recommended action: run `python test_gemini.py` to detect which Gemini models support streaming for your API key. If streaming is unreliable for your key, use `gemini-2.5-pro` (non-streaming) as the default and rely on the fallback.



================================================
FILE: docs/TODO.md
================================================
# TODO - Next Steps

This file lists recommended next steps to harden and productionize the WebSocket streaming and token/subscription system.

1. Database migration
   - Implement PostgreSQL + SQLModel/SQLAlchemy async and Alembic migrations.
   - Create core tables: users, subscriptions, messages, cost_tracker, api_usage.

2. Atomic token deduction
   - Replace in-memory deduction with DB transactions using `SELECT FOR UPDATE`.
   - Add tests for concurrent deductions.

3. Provider streaming
   - Ensure `stream_generate()` is implemented for all providers (OpenAI, Anthropic, Gemini).
   - Add unit tests and a mock streaming provider for local tests.

4. Authentication
   - Replace simple `user_id` acceptance with authenticated sessions / API keys.
   - Store API keys (rotatable) and usage limits in DB.

5. Metrics & Monitoring
   - Add Prometheus metrics for active connections, stream durations, API errors, and costs.
   - Add alerting for high cost spikes.

6. Scale-out
   - Use Redis for rate limits and cross-worker presence.
   - Implement sticky sessions or centralize streaming via pub/sub if multiple workers serve the same client.

7. Billing
   - Add periodic billing job to summarize cost_tracker and invoice users.

8. UI improvements
   - Serve a nicer test client and a simple admin UI to view usage and costs.

9. Tests & CI
   - Add integration tests for websocket flows.
   - Add CI pipeline that runs unit and integration tests.

10. Security review
    - Audit endpoints for injection, rate-limiting, and secrets management.

Feel free to pick items to implement next; I can start with the DB migration or provider streaming (Gemini) as you prefer.



================================================
FILE: hooks/use-chat-sse.ts
================================================
"use client"

import { useState, useRef, useCallback } from "react"
import type { Message } from "@/lib/api"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface SSEMessage {
  type: "chunk" | "done" | "error"
  content?: string
  tokens_used?: number
  tokens_remaining?: number
  credits_used?: number
  credits_remaining?: number
  model?: string
  error?: string
  message?: string
}

interface UsageDelta {
  tokens_remaining: number
  credits_remaining: number
}

export function useChatSSE(userId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [usage, setUsage] = useState<UsageDelta | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (prompt: string, model: string, onUsageUpdate?: (usage: UsageDelta) => void) => {
      setError(null)
      setUsage(null)

      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: prompt,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMessage])

      // Create assistant message placeholder
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])

      setIsStreaming(true)
      abortControllerRef.current = new AbortController()

      try {
        const response = await fetch(`${API_URL}/stream/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            model,
            user_id: userId,
            max_tokens: 1000,
            temperature: 0.7,
          }),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        if (!response.body) {
          throw new Error("No response body")
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split("\n\n")
          buffer = events.pop() || ""

          for (const event of events) {
            if (!event.trim()) continue

            const lines = event.split("\n")
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const jsonStr = line.slice(6)
                try {
                  const data: SSEMessage = JSON.parse(jsonStr)

                  if (data.type === "chunk" && data.content) {
                    setMessages((prev) => {
                      const updated = [...prev]
                      updated[updated.length - 1].content += data.content || ""
                      return updated
                    })
                  } else if (data.type === "done") {
                    setMessages((prev) => {
                      const updated = [...prev]
                      updated[updated.length - 1].tokens_used = data.tokens_used
                      updated[updated.length - 1].credits_used = data.credits_used
                      updated[updated.length - 1].model = data.model
                      return updated
                    })

                    if (data.tokens_remaining !== undefined) {
                      const delta = {
                        tokens_remaining: data.tokens_remaining,
                        credits_remaining: data.credits_remaining || 0,
                      }
                      setUsage(delta)
                      onUsageUpdate?.(delta)
                    }

                    setIsStreaming(false)
                  } else if (data.type === "error") {
                    setError(data.message || data.error || "Stream error")
                    setIsStreaming(false)
                  }
                } catch (e) {
                  console.error("Failed to parse SSE data:", e)
                }
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError(err.message || "Streaming failed")
          console.error("Streaming failed:", err)
        }
        setIsStreaming(false)
      }
    },
    [userId],
  )

  const stopGeneration = useCallback(() => {
    abortControllerRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return {
    messages,
    sendMessage,
    isStreaming,
    error,
    usage,
    stopGeneration,
    clearMessages: () => setMessages([]),
  }
}




================================================
FILE: hooks/use-mobile.ts
================================================
import * as React from 'react'

const MOBILE_BREAKPOINT = 768

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    }
    mql.addEventListener('change', onChange)
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return !!isMobile
}




================================================
FILE: lib/api.ts
================================================
// API client configured to connect to FastAPI backend
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  model?: string
  tokens_used?: number
  credits_used?: number
  timestamp: Date
}

export interface TokenUsage {
  tokens_used: number
  tokens_remaining: number
  tokens_limit: number
  credits_used: number
  credits_remaining: number
  credits_limit: number
  percentage_used: number
}

export interface Subscription {
  id: string
  user_id: string
  tier_name: "Free" | "Pro" | "Enterprise"
  tier_id: "free" | "pro" | "enterprise"
  allowed_models: string[]
  tokens_limit: number
  tokens_used: number
  tokens_remaining: number
  credits_limit: number
  credits_used: number
  credits_remaining: number
  status: "active" | "expired" | "suspended"
  monthly_cost_usd: number
}

export interface Model {
  value: string
  label: string
  tier: "free" | "pro" | "enterprise"
  provider: "gemini" | "openai" | "anthropic" | "mock"
}

export interface AdminStats {
  total_users_with_usage: number
  total_api_calls_made: number
  total_tokens_consumed: number
  total_cost_usd: number
  by_provider: {
    [provider: string]: {
      calls: number
      tokens: number
      cost: number
    }
  }
}

export async function getTokenUsage(userId: string): Promise<TokenUsage> {
  const res = await fetch(`${API_URL}/subscriptions/${userId}`)
  if (!res.ok) throw new Error("Failed to fetch token usage")
  const data = await res.json()
  // Transform FastAPI response to match frontend interface
  return {
    tokens_used: data.tokens_used || 0,
    tokens_remaining: data.tokens_remaining || 0,
    tokens_limit: data.tokens_limit || 0,
    credits_used: data.credits_used || 0,
    credits_remaining: data.credits_remaining || 0,
    credits_limit: data.credits_limit || 0,
    percentage_used: data.tokens_limit > 0 ? (data.tokens_used / data.tokens_limit) * 100 : 0,
  }
}

export async function getSubscription(userId: string): Promise<Subscription> {
  const res = await fetch(`${API_URL}/subscriptions/${userId}`)
  if (!res.ok) throw new Error("Failed to fetch subscription")
  const data = await res.json()
  // Transform FastAPI response
  return {
    id: data.id || `sub-${userId}`,
    user_id: userId,
    tier_name: data.tier_name || "Free",
    tier_id: data.tier_id || "free",
    allowed_models: data.allowed_models || [],
    tokens_limit: data.tokens_limit || 1000,
    tokens_used: data.tokens_used || 0,
    tokens_remaining: data.tokens_remaining || 1000,
    credits_limit: data.credits_limit || 500,
    credits_used: data.credits_used || 0,
    credits_remaining: data.credits_remaining || 500,
    status: data.status || "active",
    monthly_cost_usd: data.monthly_cost_usd || 0,
  }
}

export async function getAdminStats(): Promise<AdminStats> {
  const res = await fetch(`${API_URL}/admin/usage`)
  if (!res.ok) throw new Error("Failed to fetch admin stats")
  return res.json()
}

export async function getAllSubscriptions(): Promise<Subscription[]> {
  const res = await fetch(`${API_URL}/admin/subscriptions`)
  if (!res.ok) throw new Error("Failed to fetch subscriptions")
  const data = await res.json()
  // Transform FastAPI response format
  if (Array.isArray(data)) {
    return data.map((sub: any) => ({
      id: `sub-${sub.user_id}`,
      user_id: sub.user_id,
      tier_name: sub.tier || sub.tier_name || "Free",
      tier_id: (sub.tier || sub.tier_name || "free").toLowerCase(),
      allowed_models: sub.allowed_models || [],
      tokens_limit: sub.tokens_limit || 1000,
      tokens_used: sub.tokens_used || 0,
      tokens_remaining: sub.tokens_remaining || 0,
      credits_limit: sub.credits_limit || 500,
      credits_used: sub.credits_used || 0,
      credits_remaining: sub.credits_remaining || 0,
      status: sub.status || "active",
      monthly_cost_usd: sub.monthly_cost_usd || 0,
    }))
  }
  return []
}

export async function addTokens(userId: string, tokens: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/add-tokens`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tokens),
  })
  if (!res.ok) throw new Error("Failed to add tokens")
  return res.json()
}

export async function addCredits(userId: string, credits: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/add-credits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credits),
  })
  if (!res.ok) throw new Error("Failed to add credits")
  return res.json()
}

export async function upgradeSubscription(userId: string, tier: string) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/upgrade?tier=${encodeURIComponent(tier)}`, {
    method: "POST",
  })
  if (!res.ok) throw new Error("Failed to upgrade subscription")
  return res.json()
}

export async function useTokens(userId: string, tokens: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/use-tokens`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tokens),
  })
  if (!res.ok) throw new Error("Failed to deduct tokens")
  return res.json()
}

export async function useCredits(userId: string, credits: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/use-credits`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credits),
  })
  if (!res.ok) throw new Error("Failed to deduct credits")
  return res.json()
}

export async function getAvailableModels(): Promise<Model[]> {
  const res = await fetch(`${API_URL}/chat/models/formatted`)
  if (!res.ok) throw new Error("Failed to fetch models")
  const data = await res.json()
  
  // Data is already in the correct format from the new endpoint
  return data
}


================================================
FILE: lib/utils.ts
================================================
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}




================================================
FILE: testing/test_llm_providers.ipynb
================================================
# Jupyter notebook converted to Python script.

"""
## How to Use in Fiesta API

Once connected, use these endpoints:

```bash
# Check available models
curl http://localhost:8000/chat/models

# Send a chat message (uses tokens)
curl -X POST http://localhost:8000/chat/ \
  -H "user-id: {user_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is AI?",
    "model": "gemini-1.5-pro",
    "max_tokens": 500
  }'

# Check tokens remaining
curl http://localhost:8000/subscriptions/{user_id}

# Check API costs so far
curl http://localhost:8000/admin/costs/{user_id}
```

### Token Flow in Each Request:

1. **Request arrives**: User sends prompt + model choice
2. **Check subscription**: Verify user has active subscription + tokens remaining
3. **Check model access**: Verify user's tier allows that model
4. **Check rate limit**: Verify user hasn't exceeded requests/minute
5. **Estimate tokens**: Count tokens in prompt
6. **Call API**: Send to OpenAI/Claude/Gemini
7. **Get response**: Receive tokens_used from API
8. **Deduct tokens**: `tokens_remaining -= tokens_used`
9. **Track cost**: `monthly_api_cost_usd += cost`
10. **Return response**: Send to user
"""

import pandas as pd

# Create summary table
summary_data = {
    "Provider": ["Gemini", "Anthropic", "OpenAI"],
    "Status": [
        "✓ Connected" if gemini_status["connected"] else "✗ Failed",
        "✓ Connected" if anthropic_status["connected"] else "✗ Failed",
        "✓ Connected" if openai_status["connected"] else "✗ Failed"
    ],
    "Error": [
        gemini_status["error"] or "None",
        anthropic_status["error"] or "None",
        openai_status["error"] or "None"
    ]
}

df = pd.DataFrame(summary_data)
print("\n" + "=" * 80)
print("CONNECTION STATUS SUMMARY")
print("=" * 80)
print(df.to_string(index=False))
print("=" * 80)

# Count working providers
working = sum([gemini_status["connected"], anthropic_status["connected"], openai_status["connected"]])
print(f"\n✓ {working}/3 providers are connected and working!")
print("\nYou can now use these providers in the Fiesta API:")
# Output:
#   

#   ================================================================================

#   CONNECTION STATUS SUMMARY

#   ================================================================================

#    Provider      Status Error

#      Gemini ✓ Connected  None

#   Anthropic ✓ Connected  None

#      OpenAI ✓ Connected  None

#   ================================================================================

#   

#   ✓ 3/3 providers are connected and working!

#   

#   You can now use these providers in the Fiesta API:


"""
## Display Connection Status Summary
"""

openai_status = {"connected": False, "error": None, "response": None}

try:
    from openai import OpenAI
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise Exception("OPENAI_API_KEY not set in .env")
    
    client = OpenAI(api_key=openai_key)
    
    # Test request
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Say 'Hello from Fiesta!' in 3 words"}
        ],
        max_tokens=100
    )
    
    openai_status["connected"] = True
    openai_status["response"] = response.choices[0].message.content
    
    print("✓ OpenAI API Connection: SUCCESS")
    print(f"Response: {openai_status['response']}")
    print(f"Model: {response.model}")
    print(f"Usage: {response.usage.prompt_tokens} input, {response.usage.completion_tokens} output")
    
except Exception as e:
    openai_status["error"] = str(e)
    print(f"✗ OpenAI API Connection: FAILED")
    print(f"Error: {openai_status['error']}")
# Output:
#   ✓ OpenAI API Connection: SUCCESS

#   Response: Hello from Fiesta!

#   Model: gpt-3.5-turbo-0125

#   Usage: 17 input, 4 output


"""
## Test OpenAI API Connection
"""

anthropic_status = {"connected": False, "error": None, "response": None}

try:
    from anthropic import Anthropic
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise Exception("ANTHROPIC_API_KEY not set in .env")
    
    client = Anthropic(api_key=anthropic_key)
    
    # Test request
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say 'Hello from Fiesta!' in 3 words"}
        ]
    )
    
    anthropic_status["connected"] = True
    anthropic_status["response"] = message.content[0].text if message.content else "No response"
    
    print("✓ Anthropic API Connection: SUCCESS")
    print(f"Response: {anthropic_status['response']}")
    print(f"Model: {message.model}")
    print(f"Usage: {message.usage.input_tokens} input, {message.usage.output_tokens} output")
    
except Exception as e:
    anthropic_status["error"] = str(e)
    print(f"✗ Anthropic API Connection: FAILED")
    print(f"Error: {anthropic_status['error']}")
# Output:
#   ✓ Anthropic API Connection: SUCCESS

#   Response: Fiesta says hello!

#   Model: claude-3-haiku-20240307

#   Usage: 21 input, 9 output


"""
## Test Anthropic API Connection
"""

gemini_status = {"connected": False, "error": None, "response": None, "model_used": None}

try:
    import google.generativeai as genai
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise Exception("GEMINI_API_KEY not set in .env")
    
    genai.configure(api_key=gemini_key)
    
    # Try latest model first: gemini-2.5-pro
    model_to_try = "gemini-2.5-pro"
    
    try:
        model = genai.GenerativeModel(model_to_try)
        response = model.generate_content("Say 'Hello from Fiesta!' in 3 words")
        gemini_status["connected"] = True
        gemini_status["response"] = response.text if hasattr(response, 'text') else str(response)
        gemini_status["model_used"] = model_to_try
    except Exception as e1:
        # Fallback: try gemini-2.5-flash
        print(f"Model {model_to_try} failed: {str(e1)}")
        model_to_try = "gemini-2.5-flash"
        print(f"Trying fallback model: {model_to_try}")
        model = genai.GenerativeModel(model_to_try)
        response = model.generate_content("Say 'Hello from Fiesta!' in 3 words")
        gemini_status["connected"] = True
        gemini_status["response"] = response.text if hasattr(response, 'text') else str(response)
        gemini_status["model_used"] = model_to_try
    
    print("✓ Gemini API Connection: SUCCESS")
    print(f"Model used: {gemini_status['model_used']}")
    print(f"Response: {gemini_status['response']}")
    
except Exception as e:
    gemini_status["error"] = str(e)
    print(f"✗ Gemini API Connection: FAILED")
    print(f"Error: {gemini_status['error']}")

# Output:
#   ✓ Gemini API Connection: SUCCESS

#   Model used: gemini-2.5-pro

#   Response: Hello from Fiesta!


"""
## Test Gemini API Connection
"""

"""
## List Available Gemini Models
"""

try:
    import google.generativeai as genai
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("✗ GEMINI_API_KEY not set in .env")
    else:
        genai.configure(api_key=gemini_key)
        
        print("Available Gemini models that support generateContent:")
        print("=" * 60)
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                print(f"  {m.name}")
        
        if not available_models:
            print("  (No models found - check API key permissions)")
        print("=" * 60)
        
except Exception as e:
    print(f"✗ Error listing Gemini models: {str(e)}")

# Output:
#   Available Gemini models that support generateContent:

#   ============================================================

#     models/gemini-2.5-flash

#     models/gemini-2.5-pro

#     models/gemini-2.0-flash-exp

#     models/gemini-2.0-flash

#     models/gemini-2.0-flash-001

#     models/gemini-2.0-flash-lite-001

#     models/gemini-2.0-flash-lite

#     models/gemini-2.0-flash-lite-preview-02-05

#     models/gemini-2.0-flash-lite-preview

#     models/gemini-2.0-pro-exp

#     models/gemini-2.0-pro-exp-02-05

#     models/gemini-exp-1206

#     models/gemini-2.5-flash-preview-tts

#     models/gemini-2.5-pro-preview-tts

#     models/gemma-3-1b-it

#     models/gemma-3-4b-it

#     models/gemma-3-12b-it

#     models/gemma-3-27b-it

#     models/gemma-3n-e4b-it

#     models/gemma-3n-e2b-it

#     models/gemini-flash-latest

#     models/gemini-flash-lite-latest

#     models/gemini-pro-latest

#     models/gemini-2.5-flash-lite

#     models/gemini-2.5-flash-image-preview

#     models/gemini-2.5-flash-image

#     models/gemini-2.5-flash-preview-09-2025

#     models/gemini-2.5-flash-lite-preview-09-2025

#     models/gemini-3-pro-preview

#     models/gemini-3-pro-image-preview

#     models/nano-banana-pro-preview

#     models/gemini-robotics-er-1.5-preview

#     models/gemini-2.5-computer-use-preview-10-2025

#   ============================================================

#     models/gemini-2.5-flash

#     models/gemini-2.5-pro

#     models/gemini-2.0-flash-exp

#     models/gemini-2.0-flash

#     models/gemini-2.0-flash-001

#     models/gemini-2.0-flash-lite-001

#     models/gemini-2.0-flash-lite

#     models/gemini-2.0-flash-lite-preview-02-05

#     models/gemini-2.0-flash-lite-preview

#     models/gemini-2.0-pro-exp

#     models/gemini-2.0-pro-exp-02-05

#     models/gemini-exp-1206

#     models/gemini-2.5-flash-preview-tts

#     models/gemini-2.5-pro-preview-tts

#     models/gemma-3-1b-it

#     models/gemma-3-4b-it

#     models/gemma-3-12b-it

#     models/gemma-3-27b-it

#     models/gemma-3n-e4b-it

#     models/gemma-3n-e2b-it

#     models/gemini-flash-latest

#     models/gemini-flash-lite-latest

#     models/gemini-pro-latest

#     models/gemini-2.5-flash-lite

#     models/gemini-2.5-flash-image-preview

#     models/gemini-2.5-flash-image

#     models/gemini-2.5-flash-preview-09-2025

#     models/gemini-2.5-flash-lite-preview-09-2025

#     models/gemini-3-pro-preview

#     models/gemini-3-pro-image-preview

#     models/nano-banana-pro-preview

#     models/gemini-robotics-er-1.5-preview

#     models/gemini-2.5-computer-use-preview-10-2025

#   ============================================================


api_keys = {
    "GEMINI": os.getenv("GEMINI_API_KEY", "NOT SET"),
    "ANTHROPIC": os.getenv("ANTHROPIC_API_KEY", "NOT SET"),
    "OPENAI": os.getenv("OPENAI_API_KEY", "NOT SET")
}

print("API Keys Status:")
print("=" * 50)
for provider, key in api_keys.items():
    status = "✓ SET" if key != "NOT SET" else "✗ NOT SET"
    key_preview = f"{key[:10]}..." if len(key) > 10 else key
    print(f"{provider:12} {status:15} {key_preview}")
# Output:
#   API Keys Status:

#   ==================================================

#   GEMINI       ✓ SET           AIzaSyC0NF...

#   ANTHROPIC    ✓ SET           sk-ant-api...

#   OPENAI       ✓ SET           sk-proj-Kf...


"""
## Set Up API Keys
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path.cwd()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load .env
from dotenv import load_dotenv
load_dotenv()

print("✓ Libraries imported")
# Output:
#   ✓ Libraries imported


"""
## Import Required Libraries
"""

"""
# LLM Provider Connection Test

This notebook tests connectivity to all three LLM providers (Gemini, Anthropic, OpenAI) and explains how token consumption works in the Fiesta API.

## How Token Usage Works

1. **User creates account** → Gets subscription (free = 1000 tokens/month)
2. **User calls `/chat/` endpoint** → Fiesta checks if they have tokens
3. **LLM API is called** → OpenAI/Claude/Gemini processes request
4. **Response received** → Tokens used = prompt tokens + completion tokens
5. **Tokens deducted** → `tokens_remaining -= tokens_used`
6. **Cost tracked** → `monthly_api_cost_usd` increases (for billing)

Each provider charges differently:
- **OpenAI**: GPT-3.5 costs ~$0.002/request, GPT-4 ~$0.015/request
- **Anthropic**: Claude 3 Haiku ~$0.001/request, Opus ~$0.075/request  
- **Gemini**: Free tier, then $0.00025 per 1K input tokens
"""


