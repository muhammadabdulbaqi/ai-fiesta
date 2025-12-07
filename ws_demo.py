"""Simple Python WebSocket demo to test the /ws/chat endpoint.

Requires: `websockets` package (pip install websockets)

Usage:
    python ws_demo.py

This script connects, sends a single chat message, prints incoming chunks and the final done message.
"""

try:
    import websockets
except Exception as e:
    print("Please install the 'websockets' package: pip install websockets")
    raise

SERVER = os.getenv('SERVER', 'ws://localhost:8000/ws/chat')
USER_ID = os.getenv('DEMO_USER', 'demo-user-1')
MODEL = os.getenv('DEMO_MODEL', 'gemini-2.5-flash')
PROMPT = os.getenv('DEMO_PROMPT', "Write a short haiku about coding")




"""
WebSocket demo disabled.

This project now uses HTTP SSE streaming at `/stream/chat`. The old `ws_demo.py` is left here for reference but is disabled.
"""
print("ws_demo.py is disabled. Use the HTTP-SSE test client at /test_client.html or run provider tests.")
if __name__ == '__main__':
    asyncio.run(run())
