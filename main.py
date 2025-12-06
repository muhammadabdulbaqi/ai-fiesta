"""Application entrypoint. Minimal app that composes routers and settings."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.on_event("startup")
async def startup_event():
    # Create demo user and subscription (kept for backwards compatibility)
    import uuid
    from datetime import datetime

    demo_user_id = str(uuid.uuid4())
    demo_user = {
        "id": demo_user_id,
        "email": settings.demo_user_email,
        "username": settings.demo_user_username,
        "hashed_password": f"hashed_{settings.demo_user_password}",
        "is_active": True,
        "created_at": datetime.now(),
    }
    models.users_db[demo_user_id] = demo_user

    demo_subscription = models.create_default_subscription(demo_user_id, "premium")
    demo_subscription["tokens_used"] = 2500
    demo_subscription["tokens_remaining"] = max(0, demo_subscription["tokens_limit"] - 2500)

    print(f"✅ Demo user created: {demo_user['email']} (ID: {demo_user_id})")
