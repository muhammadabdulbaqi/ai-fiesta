"""Application entrypoint - FIXED VERSION with better error handling."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.database import init_db
from app.routers import users as users_router
from app.routers import subscriptions as subscriptions_router
from app.routers import chat as chat_router
from app.routers import admin as admin_router
from app.routers import auth as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup"""
    # Always initialize database
    await init_db()
    print("✅ Database initialized")
    
    yield
    
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
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
        "mode": "database",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    from datetime import datetime
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": settings.version,
        "database": True,
    }

