# AI Fiesta — Multi-Provider AI Chat Platform

A modern full-stack AI chat application that supports multiple LLM providers (OpenAI, Anthropic, Gemini, Grok, Perplexity) with real-time streaming, authentication, and usage tracking.

## Project Structure

```
fiesta/
├── backend/          # FastAPI backend application
│   ├── app/          # Application code
│   ├── alembic/      # Database migrations
│   ├── main.py       # Application entrypoint
│   └── requirements.txt
├── frontend/         # Next.js frontend application
│   ├── app/          # Next.js pages
│   ├── components/   # React components
│   ├── lib/          # Utilities and API client
│   └── package.json
├── docs/             # Documentation files
│   ├── QUICKSTART.md
│   ├── MODEL_PRICING_GUIDE.md
│   ├── FRONTEND_CUSTOMIZATION_GUIDE.md
│   └── ... (other guides)
├── admin/            # Admin panel (future)
└── archive/          # Archived files (ignored by git)
```

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker** (for PostgreSQL database)
- **PostgreSQL** (via Docker or local installation)

## Quick Start Guide

### Step 1: Start the Database

The application uses PostgreSQL. Start it with Docker:

```bash
cd backend
docker-compose up -d
```

This will start PostgreSQL on port **5433** (to avoid conflicts with your desktop pgAdmin).

Verify it's running:
```bash
docker ps
```

### Step 2: Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   
   # Mac/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file in the `backend/` directory:**
   ```bash
   # Copy from the sample
   cp "../.env sample" .env
   ```

   Then edit `.env` and add your API keys:
   ```ini
   # Required: At least one API key for the providers you want to use
   OPENAI_API_KEY=your_openai_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   GEMINI_API_KEY=your_gemini_key_here
   GROK_API_KEY=your_grok_key_here          # Optional
   PERPLEXITY_API_KEY=your_perplexity_key  # Optional
   
   # Database (already configured for Docker)
   DATABASE_URL=postgresql+asyncpg://fiesta_user:fiesta_pass@localhost:5433/fiesta_db
   
   # JWT Authentication (change in production!)
   JWT_SECRET_KEY=your-secret-key-change-in-production
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_HOURS=24
   
   # CORS (allow frontend)
   CORS_ALLOW_ORIGINS=["http://localhost:3000"]
   ```

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the backend server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

   The API will be available at:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Step 3: Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create `.env.local` file in the `frontend/` directory:**
   ```ini
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at: http://localhost:3000

### Step 4: First Time Setup

1. **Open the application:**
   Navigate to http://localhost:3000

2. **Create an account:**
   - Click "Sign up" or go to http://localhost:3000/register
   - Enter your email, username, and password
   - You'll automatically get a Free tier subscription

3. **Start chatting:**
   - Select one or more AI models
   - Type your message and send
   - Watch responses stream in real-time!

## Features

### Multi-Chat Mode
- Select multiple AI models simultaneously
- Compare responses side-by-side
- Horizontal scrolling for model selection

### Super Fiesta Mode
- Single model selection with dropdown
- Focused conversation experience

### Authentication
- JWT-based authentication
- Secure password hashing (bcrypt)
- User registration and login

### Conversation History
- View all past conversations
- Delete conversations
- Conversation titles auto-generated from first message

### Dark Mode
- Toggle between light and dark themes
- System preference detection

### Usage Tracking
- Real-time token and credit tracking
- Cost tracking per conversation
- Admin dashboard for system-wide analytics

## Supported AI Providers

- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo, O1-mini, O1-preview
- **Anthropic**: Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku
- **Google Gemini**: Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash, Gemini 1.5 Pro, Gemini 1.5 Flash
- **Grok** (X.AI): Grok Beta, Grok 2
- **Perplexity**: Sonar, Sonar Pro

See [Model Pricing Guide](./docs/MODEL_PRICING_GUIDE.md) for detailed pricing and recommendations.

## Database Management

See the [Database Management Guide](./docs/DATABASE_MANAGEMENT_GUIDE.md) and [Database Viewing Guide](./docs/DATABASE_VIEWING_GUIDE.md) for detailed instructions.

### Quick Commands

**Using Docker:**
```bash
cd backend
docker-compose up -d    # Start
docker-compose down     # Stop
docker-compose logs     # View logs
```

**Database Migrations:**
```bash
cd backend
alembic upgrade head    # Apply migrations
```

## Environment Variables

### Backend (.env in `backend/` directory)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Yes (change in production!) |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `GEMINI_API_KEY` | Google Gemini API key | Optional |
| `GROK_API_KEY` | X.AI Grok API key | Optional |
| `PERPLEXITY_API_KEY` | Perplexity API key | Optional |
| `CORS_ALLOW_ORIGINS` | Allowed CORS origins | Yes |

### Frontend (.env.local in `frontend/` directory)

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes |

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Chat
- `POST /chat/` - Send chat message (non-streaming)
- `POST /stream/chat` - Stream chat response (SSE)
- `GET /conversations/` - List user's conversations
- `GET /conversations/{id}/messages` - Get conversation messages
- `DELETE /conversations/{id}` - Delete conversation

### Models
- `GET /chat/models` - List available models
- `GET /chat/models/formatted` - Get formatted model info with pricing

### Admin
- `GET /admin/usage` - System-wide usage stats
- `GET /admin/costs` - Cost breakdown by provider
- `GET /admin/subscriptions` - All user subscriptions

## Troubleshooting

### Database Connection Issues
- **Port conflict**: Make sure port 5433 is available (Docker uses this to avoid conflicts)
- **Connection refused**: Ensure Docker container is running: `docker ps`
- **Wrong credentials**: Check `docker-compose.yml` and `.env` match

### Backend Won't Start
- **Missing dependencies**: Run `pip install -r requirements.txt`
- **Database not running**: Start Docker: `docker-compose up -d`
- **Port 8000 in use**: Change port in uvicorn command or kill process using port 8000

### Frontend Won't Connect
- **CORS errors**: Check `CORS_ALLOW_ORIGINS` in backend `.env` includes `http://localhost:3000`
- **API URL wrong**: Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- **Backend not running**: Ensure backend is running on port 8000

### Authentication Issues
- **Token expired**: Login again to get a new token
- **401 errors**: Make sure you're logged in and token is valid
- **Registration fails**: Check database is running and migrations are applied

### No AI Responses
- **Missing API keys**: Add at least one provider API key to backend `.env`
- **Rate limits**: Free tier API keys have rate limits
- **Model not available**: Check your subscription tier allows the selected model

## Development

### Running in Development Mode

**Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### Building for Production

**Backend:**
```bash
cd backend
pip install -r requirements.txt
# Use a production ASGI server like gunicorn with uvicorn workers
```

**Frontend:**
```bash
cd frontend
npm run build
npm start
```

## Documentation

All documentation is located in the [`docs/`](./docs/) folder:

- **[Quick Start Guide](./docs/QUICKSTART.md)** - Get up and running quickly
- **[Model Pricing Guide](./docs/MODEL_PRICING_GUIDE.md)** - Compare models by price and use case
- **[Frontend Customization Guide](./docs/FRONTEND_CUSTOMIZATION_GUIDE.md)** - Customize logo, colors, branding
- **[Database Viewing Guide](./docs/DATABASE_VIEWING_GUIDE.md)** - View database contents with pgAdmin
- **[Database Management Guide](./docs/DATABASE_MANAGEMENT_GUIDE.md)** - Database operations and migrations
- **[Environment Setup Guide](./docs/ENV_SETUP_GUIDE.md)** - Configure environment variables
- **[Usage Limits Guide](./docs/USAGE_LIMITS_GUIDE.md)** - Understand credit and token limits
- **[Adding Users via pgAdmin](./docs/ADDING_USERS_VIA_PGADMIN.md)** - Manual user creation
- **[Quick Admin Setup](./docs/QUICK_ADMIN_SETUP.md)** - Set up admin users

## Project Status

✅ **Completed:**
- Multi-provider LLM support (OpenAI, Anthropic, Gemini, Grok, Perplexity)
- JWT authentication system
- PostgreSQL database integration
- Real-time SSE streaming
- Conversation history with multi-model support
- Dark mode
- Admin dashboard
- Usage and cost tracking
- Multi-Chat and Super Fiesta modes
- Model selection with provider icons

## License

MIT
