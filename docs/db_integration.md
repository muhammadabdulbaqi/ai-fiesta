# Database & ORM Integration Plan

This document outlines recommended design for integrating PostgreSQL and an async ORM into Fiesta for managing users, subscriptions, tokens, messages, and billing.

## Goals

- Provide durable storage for users, subscriptions, messages, and API usage
- Ensure atomic token deductions (no double-spend)
- Support migrations, connection pooling, and async access
- Be ready for scaling (multiple app workers, Redis for cross-worker coordination)

## Recommended Stack

- PostgreSQL (production)
- SQLAlchemy (1.4+) with async support + `asyncpg` driver OR `SQLModel` (Pydantic-style on top of SQLAlchemy)
- Alembic for migrations
- Redis (optional) for rate-limiting, presence, pub/sub across workers

## Core Tables / Models

- `users`:
  - id (PK, UUID)
  - email
  - username
  - hashed_password (nullable if using third-party auth)
  - created_at

- `subscriptions`:
  - id (PK, UUID)
  - user_id (FK -> users.id)
  - tier_id (free/pro/enterprise)
  - tokens_limit (int)
  - tokens_used (int)
  - tokens_remaining (int)
  - monthly_api_cost_usd (float)
  - status (active/paused/cancelled)
  - created_at, expires_at

- `conversations`:
  - id (PK, UUID)
  - user_id (FK)
  - created_at

- `messages`:
  - id (PK, UUID)
  - conversation_id (FK)
  - user_id (FK)
  - role (user/assistant/system)
  - content (text)
  - model (text)
  - prompt_tokens (int)
  - completion_tokens (int)
  - total_tokens (int)
  - api_cost_usd (float)
  - created_at

- `api_usage` or `cost_tracker`:
  - id (PK, UUID)
  - user_id (FK)
  - provider (text)
  - model (text)
  - prompt_tokens (int)
  - completion_tokens (int)
  - total_tokens (int)
  - cost_usd (float)
  - created_at

## Atomic Token Deduction

To prevent race conditions when multiple concurrent requests attempt to deduct tokens:

1. Start a DB transaction (async session)
2. SELECT subscription row `FOR UPDATE` to lock it
3. Verify `tokens_remaining >= tokens_to_deduct`
4. Update `tokens_used` and `tokens_remaining`
5. Commit transaction

If the transaction fails, return a 409-like error and retry logic on the client if appropriate.

## Migrations

- Use Alembic to manage schema changes
- Keep migration scripts in `alembic/` folder; run `alembic upgrade head` as part of deployment

## Scaling

- Use connection pooling (`asyncpg` + SQLAlchemy pooling) to handle concurrent DB connections
- Use Redis for rate limit counters and for cross-worker active-connection registry if you host multiple app workers

## Implementation Notes

- Start with `SQLModel` for quick wins; later migrate to full SQLAlchemy if you need complex relations/optimizations.
- Wrap DB writes for billing and analytics in background tasks if they are non-critical for the websocket response latency (but for token deduction do it synchronously in the transaction).

## Next Steps

- Add `requirements.txt` entries: `sqlmodel`, `asyncpg`, `alembic` (or `sqlalchemy` + `asyncpg` + `alembic`)
- Create initial migration with the core tables
- Implement `database.py` with `async_engine` and session helpers
- Replace in-memory stores with DB-backed models gradually
