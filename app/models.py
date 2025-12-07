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

