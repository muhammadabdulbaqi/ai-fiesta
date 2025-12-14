"""In-memory data structures and helper functions."""
import uuid
from datetime import datetime
from typing import Dict

# In-memory stores (legacy)
users_db: Dict[str, dict] = {}
subscriptions_db: Dict[str, dict] = {}
cost_tracker_db: Dict[str, dict] = {} 
api_usage_db: Dict[str, dict] = {} 

# --- MODEL METADATA & PRICING ---
# This serves as the source of truth for the Frontend "Pricing" page
MODEL_META = {
    "gemini-2.5-flash": {
        "label": "Gemini 2.5 Flash",
        "provider": "gemini",
        "description": "Fast, multimodal, and efficient.",
        "input_cost_1k": 0.0001,  # Example pricing
        "output_cost_1k": 0.0004,
        "credit_multiplier": 0.005 # Internal credit logic
    },
    "gemini-2.5-pro": {
        "label": "Gemini 2.5 Pro",
        "provider": "gemini",
        "description": "Reasoning and complex tasks.",
        "input_cost_1k": 0.00125,
        "output_cost_1k": 0.00375,
        "credit_multiplier": 0.04
    },
    "gpt-3.5-turbo": {
        "label": "GPT-3.5 Turbo",
        "provider": "openai",
        "description": "Fast and reliable everyday model.",
        "input_cost_1k": 0.0005,
        "output_cost_1k": 0.0015,
        "credit_multiplier": 0.01
    },
    "gpt-4o": {
        "label": "GPT-4o",
        "provider": "openai",
        "description": "Flagship high-intelligence model.",
        "input_cost_1k": 0.005,
        "output_cost_1k": 0.015,
        "credit_multiplier": 0.1
    },
    "claude-3-haiku-20240307": {
        "label": "Claude 3 Haiku",
        "provider": "anthropic",
        "description": "Fastest Claude model.",
        "input_cost_1k": 0.00025,
        "output_cost_1k": 0.00125,
        "credit_multiplier": 0.02
    },
    "claude-3-5-sonnet-20240620": {
        "label": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "description": "High intelligence, balanced speed.",
        "input_cost_1k": 0.003,
        "output_cost_1k": 0.015,
        "credit_multiplier": 0.1
    }
}

# Generate simple lookup for cost estimation logic
MODEL_CREDIT_COSTS = {k: v["credit_multiplier"] for k, v in MODEL_META.items()}
MODEL_CREDIT_COSTS["default"] = 0.01

# --- SUBSCRIPTION TIERS ---
SUBSCRIPTION_TIERS = {
    "free": {
        "tier_id": "free",
        "name": "Free",
        "allowed_models": ["gemini-2.5-flash", "gpt-3.5-turbo"],
        "tokens_per_month": 5000,
        "credits_per_month": 5000,
        "rate_limit_per_minute": 5,
        "cost_usd": 0.0,
    },
    "pro": {
        "tier_id": "pro",
        "name": "Pro",
        "allowed_models": [
            "gemini-2.5-flash", "gemini-2.5-pro",
            "gpt-3.5-turbo", "gpt-4o",
            "claude-3-haiku-20240307", "claude-3-5-sonnet-20240620"
        ],
        "tokens_per_month": 100000,
        "credits_per_month": 50000,
        "rate_limit_per_minute": 60,
        "cost_usd": 19.99,
    },
    "enterprise": {
        "tier_id": "enterprise",
        "name": "Enterprise",
        "allowed_models": list(MODEL_META.keys()), # All models
        "tokens_per_month": 1000000,
        "credits_per_month": 1000000,
        "rate_limit_per_minute": 500,
        "cost_usd": 199.99,
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
        "monthly_api_cost_usd": 0.0,  
        "rate_limit_per_minute": tier["rate_limit_per_minute"],
        "created_at": datetime.now(),
        "expires_at": None,
    }
    subscriptions_db[subscription["id"]] = subscription
    return subscription