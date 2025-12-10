# Fiesta — Full Stack AI Chat Platform

Fiesta is a modern, full-stack AI chat application that orchestrates multiple LLM providers (Gemini, OpenAI, Anthropic) with a unified streaming interface and a credit-based usage tracking system.

It consists of:
- **Backend:** FastAPI application with SSE streaming, provider abstraction, and subscription management.
- **Frontend:** Next.js (App Router) application with a responsive chat UI, real-time token tracking, and admin dashboard.

---

## 🚀 Features

- **Multi-Provider Support:** Seamlessly switch between Google Gemini, OpenAI (GPT-4/3.5), and Anthropic (Claude) models.
- **Real-Time Streaming:** Robust Server-Sent Events (SSE) implementation for typewriter-style responses.
- **Usage Tracking:** Granular accounting of tokens and "credits" per request.
- **Subscription Simulation:** In-memory tier system (Free, Pro, Enterprise) enforcing rate limits and model access.
- **Admin Dashboard:** View system-wide usage, costs, and manage user credits.
- **Modern UI:** Built with Next.js, Tailwind CSS, and Shadcn/UI.

---

## 🛠️ Tech Stack

### Backend (`/app`)
- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Streaming:** Server-Sent Events (SSE)
- **Database:** In-memory (Python dictionaries) for rapid prototyping (Migration to Postgres planned).

### Frontend (`/`)
- **Framework:** Next.js 15+ (App Router)
- **Styling:** Tailwind CSS, Shadcn/UI
- **State/Hooks:** Custom SSE hooks for reliable stream handling.

---

## ⚡ Quick Start (Local Development)

You need **Python 3.11+** and **Node.js 18+** installed.

### 1. Backend Setup

1. Create a virtual environment and install dependencies:
   ```powershell
   # Windows
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   
   # Mac/Linux
   # python3 -m venv .venv
   # source .venv/bin/activate

   pip install -r requirements.txt
   ```

2. Configure Environment Variables:
   Create a `.env` file in the root directory (or set them in your shell):
   ```ini
   # LLM API Keys (at least one is recommended)
   GEMINI_API_KEY=your_gemini_key
   OPENAI_API_KEY=your_openai_key
   ANTHROPIC_API_KEY=your_anthropic_key
   
   # App Config
   CORS_ALLOW_ORIGINS=["http://localhost:3000"]
   ```

3. Run the Backend:
   ```powershell
   uvicorn main:app --reload --port 8000
   ```
   The API will be available at `http://localhost:8000`.

### 2. Frontend Setup

1. Install Node dependencies:
   ```bash
   npm install
   # or yarn install
   ```

2. Configure Frontend Environment:
   Create a `.env.local` file in the root:
   ```ini
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_DEFAULT_USER_ID=demo-user-1
   ```

3. Run the Frontend:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📂 Project Structure

```
fiesta/
├── app/                    # FastAPI Backend
│   ├── routers/            # API Endpoints (chat, admin, subscriptions)
│   ├── llm/                # Provider adapters (Gemini, OpenAI, Anthropic)
│   ├── models.py           # In-memory database schemas
│   └── main.py             # App entrypoint
├── components/             # React Components (UI)
├── hooks/                  # Custom React Hooks (use-chat-sse)
├── lib/                    # Frontend utilities & API client
├── public/                 # Static assets
├── README.md               # This file
├── requirements.txt        # Python dependencies
└── package.json            # Node.js dependencies
```

---

## 🧪 Testing

### Backend Only
You can test the streaming endpoint without the frontend using the included HTML client:
1. Ensure backend is running on port 8000.
2. Open `http://localhost:8000/test_client.html` in your browser.
3. This isolates backend SSE logic from React state logic.

### Provider Verification
Run the included script to check which API keys are working and which models are available:
```bash
python testing/test_providers.py --check-keys
python testing/test_gemini.py
```

---

## 🗺️ Roadmap & Status

### ✅ Phase 1: Foundation (Completed)
- [x] FastAPI backend with SSE streaming.
- [x] Pluggable provider architecture.
- [x] Basic Next.js frontend scaffolding.
- [x] Credit/Token deduction logic.

### 🚧 Phase 2: Stability & Experience (Current Focus)
- [ ] **Fix Streaming Bug:** Resolve issue where text duplicates/splits mid-word in the UI.
- [ ] **Multi-Model Toggle:** Allow selecting multiple active models to compare responses side-by-side.
- [ ] **Conversation History:** Persist chat history in the UI sidebar.

### 🔮 Phase 3: Production Hardening (Next)
- [ ] **Database Integration:** Migrate from in-memory dicts to PostgreSQL + SQLModel.
- [ ] **Authentication:** Replace hardcoded `demo-user-1` with real Auth (e.g., NextAuth/Clerk).
- [ ] **LangGraph:** Integrate for complex agentic workflows.

---

## 🐞 Troubleshooting

- **CORS Errors:** Ensure `CORS_ALLOW_ORIGINS` in `app/config.py` or `.env` matches your frontend URL (`http://localhost:3000`).
- **Streaming Issues:** If no text appears, check the backend console. If `google-generativeai` is missing, the backend defaults to a Mock provider.
- **"429 Quota Exceeded":** This is common with free tier keys. The backend handles this gracefully by sending an error event to the client.
