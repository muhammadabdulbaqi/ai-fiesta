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

