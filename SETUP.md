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

