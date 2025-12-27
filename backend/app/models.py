"""Model metadata and subscription tier definitions."""
# This serves as the source of truth for the Frontend "Pricing" page

# Credit normalization constants
# Base credit value: 1 credit = $0.001 per 1k tokens (1 mill per credit)
# This ensures fair pricing where same dollar cost = same credits across all models
CREDIT_BASE_VALUE = 0.001  # $0.001 per 1k tokens per credit

# Typical token ratio: 1 input token : 3 output tokens (based on average usage)
# Used for calculating weighted average cost
TYPICAL_INPUT_RATIO = 1
TYPICAL_OUTPUT_RATIO = 3
TYPICAL_TOTAL_RATIO = TYPICAL_INPUT_RATIO + TYPICAL_OUTPUT_RATIO


def calculate_normalized_credit_multiplier(input_cost_1k: float, output_cost_1k: float) -> float:
    """
    Calculate normalized credit multiplier based on actual provider costs.
    
    Formula:
    1. Calculate weighted average cost per 1k tokens (assuming 1:3 input:output ratio)
    2. Normalize to base credit value: multiplier = avg_cost / CREDIT_BASE_VALUE
    
    This ensures that 1 credit = same dollar value across all models.
    
    Args:
        input_cost_1k: Cost per 1k input tokens in USD
        output_cost_1k: Cost per 1k output tokens in USD
    
    Returns:
        Normalized credit multiplier
    """
    # Weighted average cost per 1k tokens
    # Typical usage: 1k input + 3k output = 4k total tokens
    weighted_avg_cost = (
        (input_cost_1k * TYPICAL_INPUT_RATIO) + 
        (output_cost_1k * TYPICAL_OUTPUT_RATIO)
    ) / TYPICAL_TOTAL_RATIO
    
    # Normalize to base credit value
    # If avg_cost = $0.001 per 1k tokens, multiplier = 1.0
    # If avg_cost = $0.01 per 1k tokens, multiplier = 10.0
    multiplier = weighted_avg_cost / CREDIT_BASE_VALUE
    
    # Round to 6 decimal places for precision
    return round(multiplier, 6)


MODEL_META = {
    "gemini-2.5-flash": {
        "label": "Gemini 2.5 Flash",
        "provider": "gemini",
        "description": "Fast, multimodal, and efficient.",
        "input_cost_1k": 0.0001,
        "output_cost_1k": 0.0004,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.0001, 0.0004)  # Normalized: 0.325
    },
    "gemini-2.5-pro": {
        "label": "Gemini 2.5 Pro",
        "provider": "gemini",
        "description": "Reasoning and complex tasks.",
        "input_cost_1k": 0.00125,
        "output_cost_1k": 0.00375,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.00125, 0.00375)  # Normalized: 3.125
    },
    "gpt-3.5-turbo": {
        "label": "GPT-3.5 Turbo",
        "provider": "openai",
        "description": "Fast and reliable everyday model.",
        "input_cost_1k": 0.0005,
        "output_cost_1k": 0.0015,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.0005, 0.0015)  # Normalized: 1.25
    },
    "gpt-4o": {
        "label": "GPT-4o",
        "provider": "openai",
        "description": "Flagship high-intelligence model.",
        "input_cost_1k": 0.005,
        "output_cost_1k": 0.015,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.005, 0.015)  # Normalized: 12.5
    },
    "claude-3-haiku-20240307": {
        "label": "Claude 3 Haiku",
        "provider": "anthropic",
        "description": "Fastest Claude model.",
        "input_cost_1k": 0.00025,
        "output_cost_1k": 0.00125,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.00025, 0.00125)  # Normalized: 1.0
    },
    "claude-3-5-sonnet-20240620": {
        "label": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "description": "High intelligence, balanced speed.",
        "input_cost_1k": 0.003,
        "output_cost_1k": 0.015,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.003, 0.015)  # Normalized: 12.0
    },
    "grok-beta": {
        "label": "Grok Beta",
        "provider": "grok",
        "description": "X.AI's Grok model with real-time knowledge.",
        "input_cost_1k": 0.001,
        "output_cost_1k": 0.003,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.001, 0.003)  # Normalized: 2.5
    },
    "grok-2": {
        "label": "Grok 2",
        "provider": "grok",
        "description": "Latest Grok model with enhanced capabilities.",
        "input_cost_1k": 0.002,
        "output_cost_1k": 0.006,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.002, 0.006)  # Normalized: 5.0
    },
    "perplexity-sonar": {
        "label": "Perplexity Sonar",
        "provider": "perplexity",
        "description": "Perplexity's search-enhanced model.",
        "input_cost_1k": 0.0005,
        "output_cost_1k": 0.002,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.0005, 0.002)  # Normalized: 1.625
    },
    "perplexity-sonar-pro": {
        "label": "Perplexity Sonar Pro",
        "provider": "perplexity",
        "description": "Advanced Perplexity model with web search.",
        "input_cost_1k": 0.001,
        "output_cost_1k": 0.004,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.001, 0.004)  # Normalized: 3.25
    },
    # Additional OpenAI models
    "gpt-4o-mini": {
        "label": "GPT-4o Mini",
        "provider": "openai",
        "description": "Fast and affordable GPT-4o variant.",
        "input_cost_1k": 0.00015,
        "output_cost_1k": 0.0006,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.00015, 0.0006)  # Normalized: 0.4875
    },
    "gpt-4-turbo": {
        "label": "GPT-4 Turbo",
        "provider": "openai",
        "description": "High-performance GPT-4 with improved speed.",
        "input_cost_1k": 0.01,
        "output_cost_1k": 0.03,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.01, 0.03)  # Normalized: 25.0
    },
    "o1-mini": {
        "label": "O1 Mini",
        "provider": "openai",
        "description": "OpenAI's reasoning model, smaller variant.",
        "input_cost_1k": 0.003,
        "output_cost_1k": 0.012,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.003, 0.012)  # Normalized: 9.75
    },
    "o1-preview": {
        "label": "O1 Preview",
        "provider": "openai",
        "description": "OpenAI's advanced reasoning model.",
        "input_cost_1k": 0.015,
        "output_cost_1k": 0.06,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.015, 0.06)  # Normalized: 48.75
    },
    # Additional Anthropic models
    "claude-3-opus-20240229": {
        "label": "Claude 3 Opus",
        "provider": "anthropic",
        "description": "Most powerful Claude model for complex tasks.",
        "input_cost_1k": 0.015,
        "output_cost_1k": 0.075,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.015, 0.075)  # Normalized: 60.0
    },
    "claude-3-5-haiku-20241022": {
        "label": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "description": "Fast and efficient Claude 3.5 variant.",
        "input_cost_1k": 0.00025,
        "output_cost_1k": 0.00125,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.00025, 0.00125)  # Normalized: 1.0
    },
    "claude-3-sonnet-20240229": {
        "label": "Claude 3 Sonnet",
        "provider": "anthropic",
        "description": "Balanced Claude 3 model.",
        "input_cost_1k": 0.003,
        "output_cost_1k": 0.015,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.003, 0.015)  # Normalized: 12.0
    },
    # Additional Gemini models
    "gemini-2.0-flash": {
        "label": "Gemini 2.0 Flash",
        "provider": "gemini",
        "description": "Fast Gemini 2.0 model.",
        "input_cost_1k": 0.0001,
        "output_cost_1k": 0.0004,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.0001, 0.0004)  # Normalized: 0.325
    },
    "gemini-pro-latest": {
        "label": "Gemini Pro Latest",
        "provider": "gemini",
        "description": "Latest Gemini Pro model.",
        "input_cost_1k": 0.00125,
        "output_cost_1k": 0.00375,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.00125, 0.00375)  # Normalized: 3.125
    },
    "gemini-flash-latest": {
        "label": "Gemini Flash Latest",
        "provider": "gemini",
        "description": "Latest Gemini Flash model.",
        "input_cost_1k": 0.0001,
        "output_cost_1k": 0.0004,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.0001, 0.0004)  # Normalized: 0.325
    },
    "gemini-1.5-pro": {
        "label": "Gemini 1.5 Pro",
        "provider": "gemini",
        "description": "Gemini 1.5 Pro with extended context.",
        "input_cost_1k": 0.00125,
        "output_cost_1k": 0.005,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.00125, 0.005)  # Normalized: 3.4375
    },
    "gemini-1.5-flash": {
        "label": "Gemini 1.5 Flash",
        "provider": "gemini",
        "description": "Fast Gemini 1.5 Flash model.",
        "input_cost_1k": 0.000075,
        "output_cost_1k": 0.0003,
        "credit_multiplier": calculate_normalized_credit_multiplier(0.000075, 0.0003)  # Normalized: 0.24375
    }
}

# Generate simple lookup for cost estimation logic
# Credit multipliers are now normalized based on actual provider costs
# 1 credit = $0.001 per 1k tokens (normalized across all models)
MODEL_CREDIT_COSTS = {k: v["credit_multiplier"] for k, v in MODEL_META.items()}
# Default multiplier for unknown models (mid-range cost)
MODEL_CREDIT_COSTS["default"] = calculate_normalized_credit_multiplier(0.001, 0.003)  # ~2.5

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
        "allowed_models": list(MODEL_META.keys()),  # All models
        "tokens_per_month": 30000,
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
    "admin": {
        "tier_id": "admin",
        "name": "Admin",
        "allowed_models": list(MODEL_META.keys()), # All models
        "tokens_per_month": 999999999,
        "credits_per_month": 999999999,
        "rate_limit_per_minute": 1000,
        "cost_usd": 0.0,
    },
}
