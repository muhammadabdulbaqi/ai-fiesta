# WebSocket Streaming - Design & Usage

This document explains the WebSocket streaming endpoint implemented in Fiesta and how to test it locally.

## Endpoint

- URL: `ws://<host>:<port>/ws/chat`
- Purpose: Stream LLM responses chunk-by-chunk to clients in real-time.

## Client → Server protocol (first message)

The client must send a JSON object immediately after connecting:

```json
{
  "type": "chat",
  "prompt": "Write a haiku about coding",
  "model": "gemini-2.5-pro",
  "conversation_id": "conv-123",
  "user_id": "demo-user-1",
  "max_tokens": 300
}
```

- `type`: must be `chat`
- `model`: model key (must be allowed by subscription). Use `gemini-2.5-pro` as the recommended default for Gemini. Availability depends on your key and region.
- `user_id`: server validates this against users stored in the system

## Server → Client messages

- Chunk messages (many):

```json
{ "type": "chunk", "content": "Once upon a time..." }
```

- Done message (single):

```json
{
  "type": "done",
  "message_id": "msg-...",
  "tokens_used": 25,
  "tokens_remaining": 975,
  "model": "gemini-2.5-flash"
}
```

- Error message (if something goes wrong):

```json
{ "type": "error", "error": "insufficient_tokens", "message": "You need 100 tokens but only have 50" }
```

## Token accounting policy (current)

- The server conservatively checks token availability before streaming, using `provider.count_tokens(prompt)` + `max_tokens`.
- Actual deduction happens after streaming completes and is based on actual produced tokens (prompt + completion).
- If the client disconnects before any chunk is sent, no tokens are deducted.
- If partial output was sent, actual produced tokens are deducted when the stream ends or when the server detects the disconnect (best-effort).

## Production considerations

- Move token accounting to a DB transaction and use `SELECT FOR UPDATE` to avoid race conditions.
- If you want to charge mid-stream, implement periodic interim commits (complex & error-prone).
- Use Redis for cross-worker presence and for rate-limiting.

## Testing locally

1. Ensure `.env` contains valid API keys (e.g. `GEMINI_API_KEY`).
2. Start the server:

```powershell
uvicorn main:app --reload
```

3. Open the test client in your browser:

 - Visit `http://localhost:8000/test_client.html` (served by FastAPI)

4. Click **Connect**, enter a prompt, click **Send**.

You should see content streamed in chunks and a final `done` message.

## Troubleshooting

- If `/test_client.html` returns an error, ensure the file exists in the project root.
- If streaming hangs: check server logs for LLM provider errors and ensure API keys are valid.

## Security

- Validate `user_id` and require authentication in production.
- Add rate-limiting and prompt length checks to prevent abuse.

## Feature flag

Set `ENABLE_WS_STREAMING=false` in `.env` to quickly disable the WebSocket endpoint.

### Gemini streaming note

- Gemini model availability and streaming support vary by key and region. Some Gemini models or keys do not support streaming (generateContent) even though they appear in `list_models()`.
- If the provider reports a streaming-related error (404 or unsupported), the app will automatically fall back to a non-streaming generate implementation for that request. The fallback behavior is logged and the client will receive a single `done` message with the final content instead of chunked `chunk` messages.

Recommended action: run `python test_gemini.py` to detect which Gemini models support streaming for your API key. If streaming is unreliable for your key, use `gemini-2.5-pro` (non-streaming) as the default and rely on the fallback.
