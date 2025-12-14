from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List, Optional

from app.db_models import Message, CostTracker, APIUsage, Conversation

async def ensure_conversation(db: AsyncSession, conversation_id: str, user_id: str) -> Conversation:
    """Get existing conversation or create a new one."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    
    if not conv:
        conv = Conversation(id=conversation_id, user_id=user_id)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv

async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    model: str = None,
    tokens: dict = None,
    cost: float = 0.0
) -> Message:
    """Save a chat message to the database."""
    tokens = tokens or {}
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model=model,
        prompt_tokens=tokens.get("prompt_tokens", 0),
        completion_tokens=tokens.get("completion_tokens", 0),
        total_tokens=tokens.get("total_tokens", 0),
        api_cost_usd=cost,
        created_at=datetime.now()
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

async def track_usage(
    db: AsyncSession,
    user_id: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float
):
    """Log detailed cost and update aggregated usage stats."""
    # 1. Detailed Log
    tracker = CostTracker(
        user_id=user_id,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=cost
    )
    db.add(tracker)

    # 2. Aggregated Stats
    result = await db.execute(
        select(APIUsage).where(
            APIUsage.user_id == user_id, 
            APIUsage.provider == provider
        )
    )
    usage = result.scalar_one_or_none()

    if not usage:
        # Create new usage record with explicit defaults
        usage = APIUsage(
            user_id=user_id, 
            provider=provider,
            calls=1,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost,
            models_used=[model],
            last_used=datetime.now()
        )
        db.add(usage)
    else:
        # Update existing record - handle None values explicitly
        usage.calls = (usage.calls or 0) + 1
        usage.prompt_tokens = (usage.prompt_tokens or 0) + prompt_tokens
        usage.completion_tokens = (usage.completion_tokens or 0) + completion_tokens
        usage.total_tokens = (usage.total_tokens or 0) + (prompt_tokens + completion_tokens)
        usage.cost_usd = (usage.cost_usd or 0.0) + cost
        usage.last_used = datetime.now()
        
        # Update models_used list safely
        current_models = list(usage.models_used) if usage.models_used else []
        if model not in current_models:
            current_models.append(model)
            usage.models_used = current_models

    await db.commit()

async def get_user_conversations(db: AsyncSession, user_id: str) -> List[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.created_at))
    )
    return result.scalars().all()

async def get_conversation_messages(db: AsyncSession, conversation_id: str) -> List[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()