from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.db_models import Message, CostTracker, APIUsage, Conversation

async def ensure_conversation(db: AsyncSession, conversation_id: str, user_id: str, title: str = None) -> Conversation:
    """Get existing conversation or create a new one."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    
    if not conv:
        # Generate title from first message if provided, otherwise use default
        if title:
            # Truncate to reasonable length
            display_title = title[:100] if len(title) > 100 else title
        else:
            display_title = f"New Chat {datetime.now().strftime('%H:%M')}"
        
        conv = Conversation(
            id=conversation_id, 
            user_id=user_id,
            title=display_title
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    elif title and not conv.title:
        # Update title if conversation exists but has no title
        conv.title = title[:100] if len(title) > 100 else title
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
    
    # Update conversation timestamp
    await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .with_for_update()
    )
    # (Trigger would normally handle this, but explicit update for now)
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

    result = await db.execute(
        select(APIUsage).where(
            APIUsage.user_id == user_id, 
            APIUsage.provider == provider
        )
    )
    usage = result.scalar_one_or_none()

    if not usage:
        usage = APIUsage(user_id=user_id, provider=provider, models_used=[])
        db.add(usage)
    
    usage.calls += 1
    usage.prompt_tokens += prompt_tokens
    usage.completion_tokens += completion_tokens
    usage.total_tokens += (prompt_tokens + completion_tokens)
    usage.cost_usd += cost
    usage.last_used = datetime.now()
    
    current_models = list(usage.models_used) if usage.models_used else []
    if model not in current_models:
        current_models.append(model)
        usage.models_used = current_models

    await db.commit()

async def get_user_conversations(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    """Get conversations with cost and token summaries."""
    # Aggregation query
    stmt = (
        select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            func.coalesce(func.sum(Message.api_cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(Message.total_tokens), 0).label("total_tokens")
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id)
        .group_by(Conversation.id)
        .order_by(desc(Conversation.created_at))
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "id": row.id,
            "title": row.title,
            "created_at": row.created_at,
            "total_cost_usd": row.total_cost,
            "total_tokens": row.total_tokens
        }
        for row in rows
    ]

async def get_conversation_messages(db: AsyncSession, conversation_id: str) -> List[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()