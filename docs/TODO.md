# TODO - Next Steps

This file lists recommended next steps to harden and productionize the WebSocket streaming and token/subscription system.

1. Database migration
   - Implement PostgreSQL + SQLModel/SQLAlchemy async and Alembic migrations.
   - Create core tables: users, subscriptions, messages, cost_tracker, api_usage.

2. Atomic token deduction
   - Replace in-memory deduction with DB transactions using `SELECT FOR UPDATE`.
   - Add tests for concurrent deductions.

3. Provider streaming
   - Ensure `stream_generate()` is implemented for all providers (OpenAI, Anthropic, Gemini).
   - Add unit tests and a mock streaming provider for local tests.

4. Authentication
   - Replace simple `user_id` acceptance with authenticated sessions / API keys.
   - Store API keys (rotatable) and usage limits in DB.

5. Metrics & Monitoring
   - Add Prometheus metrics for active connections, stream durations, API errors, and costs.
   - Add alerting for high cost spikes.

6. Scale-out
   - Use Redis for rate limits and cross-worker presence.
   - Implement sticky sessions or centralize streaming via pub/sub if multiple workers serve the same client.

7. Billing
   - Add periodic billing job to summarize cost_tracker and invoice users.

8. UI improvements
   - Serve a nicer test client and a simple admin UI to view usage and costs.

9. Tests & CI
   - Add integration tests for websocket flows.
   - Add CI pipeline that runs unit and integration tests.

10. Security review
    - Audit endpoints for injection, rate-limiting, and secrets management.

Feel free to pick items to implement next; I can start with the DB migration or provider streaming (Gemini) as you prefer.
