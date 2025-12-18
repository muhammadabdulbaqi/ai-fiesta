"""SQLAlchemy database models"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    suspended = "suspended"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    tier_id = Column(String, nullable=False)
    tier_name = Column(String, nullable=False)
    plan_type = Column(String, nullable=False)
    
    # Store allowed_models as JSON array
    allowed_models = Column(JSON, nullable=False, default=list)
    
    tokens_limit = Column(Integer, nullable=False)
    tokens_used = Column(Integer, default=0)
    tokens_remaining = Column(Integer, nullable=False)
    
    credits_limit = Column(Integer, nullable=False)
    credits_used = Column(Integer, default=0)
    credits_remaining = Column(Integer, nullable=False)
    
    monthly_cost_usd = Column(Float, default=0.0)
    monthly_api_cost_usd = Column(Float, default=0.0)
    rate_limit_per_minute = Column(Integer, nullable=False)
    
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.active)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscription")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    model = Column(String, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    api_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class CostTracker(Base):
    __tablename__ = "cost_tracker"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False)
    
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    
    cost_usd = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now, index=True)


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    
    # FIX: Add default=0 and nullable=False to prevent None values
    calls = Column(Integer, default=0, nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    cost_usd = Column(Float, default=0.0, nullable=False)
    
    # Store models_used as JSON array
    models_used = Column(JSON, default=list, nullable=False)
    
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)