"""Application entrypoint - FIXED VERSION with better error handling."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from fastapi.responses import FileResponse
import traceback

from app.config import settings
from app.database import init_db
from app.routers import users as users_router
from app.routers import subscriptions as subscriptions_router
from app.routers import chat as chat_router
from app.routers import admin as admin_router
from app import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup"""
    # Initialize database if enabled
    if settings.use_database:
        await init_db()
        print("✅ Database initialized")
    
    # Create demo user (in-memory OR database)
    from datetime import datetime
    
    demo_user_id = "demo-user-1"
    
    if settings.use_database:
        # Create demo user in database
        from app.services import user_service
        from app.database import async_session_maker
        
        async with async_session_maker() as db:
            try:
                existing = await user_service.get_user_by_id(db, demo_user_id)
                if not existing:
                    # Create with specific ID
                    from app.db_models import User, Subscription
                    
                    user = User(
                        id=demo_user_id,
                        email=settings.demo_user_email,
                        username=settings.demo_user_username,
                        hashed_password=f"hashed_{settings.demo_user_password}",
                        is_active=True,
                    )
                    db.add(user)
                    await db.flush()
                    
                    tier = models.SUBSCRIPTION_TIERS["free"]
                    subscription = Subscription(
                        user_id=user.id,
                        tier_id=tier["tier_id"],
                        tier_name=tier["name"],
                        plan_type="free",
                        allowed_models=tier["allowed_models"],
                        tokens_limit=tier["tokens_per_month"],
                        tokens_used=0,
                        tokens_remaining=tier["tokens_per_month"],
                        credits_limit=tier.get("credits_per_month", tier["tokens_per_month"]),
                        credits_used=0,
                        credits_remaining=tier.get("credits_per_month", tier["tokens_per_month"]),
                        monthly_cost_usd=tier["cost_usd"],
                        rate_limit_per_minute=tier["rate_limit_per_minute"],
                    )
                    db.add(subscription)
                    
                    # CRITICAL: Commit before checking
                    await db.commit()
                    
                    # Refresh to load the data
                    await db.refresh(user)
                    await db.refresh(subscription)
                    
                    print(f"✅ Demo user created in database: {user.email}")
                    print(f"✅ Subscription created: {subscription.tier_name} tier")
                else:
                    print(f"✅ Demo user already exists: {existing.email}")
                    # Verify subscription exists
                    sub = await user_service.get_subscription(db, demo_user_id)
                    if sub:
                        print(f"✅ Subscription found: {sub.tier_name} tier")
                    else:
                        print("⚠️ WARNING: User exists but has no subscription!")
                        # Create subscription for existing user
                        tier = models.SUBSCRIPTION_TIERS["free"]
                        subscription = Subscription(
                            user_id=existing.id,
                            tier_id=tier["tier_id"],
                            tier_name=tier["name"],
                            plan_type="free",
                            allowed_models=tier["allowed_models"],
                            tokens_limit=tier["tokens_per_month"],
                            tokens_used=0,
                            tokens_remaining=tier["tokens_per_month"],
                            credits_limit=tier.get("credits_per_month", tier["tokens_per_month"]),
                            credits_used=0,
                            credits_remaining=tier.get("credits_per_month", tier["tokens_per_month"]),
                            monthly_cost_usd=tier["cost_usd"],
                            rate_limit_per_minute=tier["rate_limit_per_minute"],
                        )
                        db.add(subscription)
                        await db.commit()
                        print(f"✅ Created missing subscription for existing user")
                        
            except Exception as e:
                print(f"❌ Error during demo user creation:")
                print(f"   {type(e).__name__}: {e}")
                traceback.print_exc()
                await db.rollback()
                # Don't raise - let the app start anyway
                print("⚠️ Continuing anyway - you may need to create users manually")
    else:
        # In-memory mode (existing logic)
        demo_user = {
            "id": demo_user_id,
            "email": settings.demo_user_email,
            "username": settings.demo_user_username,
            "hashed_password": f"hashed_{settings.demo_user_password}",
            "is_active": True,
            "created_at": datetime.now(),
        }
        
        if demo_user_id not in models.users_db:
            models.users_db[demo_user_id] = demo_user
        
        demo_subscription = models.create_default_subscription(demo_user_id, "free")
        print(f"✅ Demo user ready (in-memory): {demo_user['email']}")
    
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
        "mode": "database" if settings.use_database else "in-memory",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    from datetime import datetime
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": settings.version,
        "database": settings.use_database,
    }


@app.get("/test_client.html", include_in_schema=False)
async def serve_test_client():
    """Serve the local HTML test client."""
    client_path = os.path.join(os.getcwd(), "test_client.html")
    if not os.path.exists(client_path):
        return {"error": "test_client.html not found in project root"}
    return FileResponse(client_path, media_type="text/html")