from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_type: str
    status: str
    tokens_limit: int
    tokens_used: int
    tokens_remaining: int
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None


class TokenUsageResponse(BaseModel):
    tokens_used: int
    tokens_remaining: int
    tokens_limit: int
    percentage_used: float
    credits_used: int | None = None
    credits_remaining: int | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str


class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = "mock"
    conversation_id: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class ChatResponse(BaseModel):
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    content: str | None = None
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    tokens_remaining: Optional[int] = None
    credits_used: Optional[int] = None
    credits_remaining: Optional[int] = None
    credits_used: Optional[int] = None
    credits_remaining: Optional[int] = None


class Conversation(BaseModel):
    id: str
    user_id: str
    created_at: datetime


class Message(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    tokens: int
    created_at: datetime


class SubscriptionTier(BaseModel):
    """Subscription tier with model access and token limits"""
    tier_id: str
    name: str  # "free", "pro", "enterprise"
    allowed_models: list[str]  # e.g. ["gemini-pro"], ["gpt-3.5-turbo", "claude-3-haiku"], etc
    tokens_per_month: int
    rate_limit_per_minute: int
    cost_usd: float  # monthly cost


class CostTracker(BaseModel):
    """Track API costs per provider and per user"""
    user_id: str
    provider: str  # "openai", "anthropic", "gemini"
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    created_at: datetime


class SubscriptionDetail(BaseModel):
    """User subscription with tier info and usage"""
    id: str
    user_id: str
    tier_id: str
    tier_name: str
    allowed_models: list[str]
    tokens_limit: int
    tokens_used: int
    tokens_remaining: int
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None
    credits_limit: int | None = None
    credits_used: int | None = None
    credits_remaining: int | None = None
    monthly_cost_usd: float
    monthly_api_cost_usd: float
    requests_this_minute: int
    status: str  # "active", "expired", "suspended"
    created_at: datetime
    expires_at: Optional[datetime]

