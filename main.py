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
