"""Simple Python WebSocket demo to test the /ws/chat endpoint.

Requires: `websockets` package (pip install websockets)

Usage:
    python ws_demo.py

This script connects, sends a single chat message, prints incoming chunks and the final done message.
"""
import asyncio
import json
import os
import sys

try:
    import websockets
except Exception as e:
    print("Please install the 'websockets' package: pip install websockets")
    raise

SERVER = os.getenv('SERVER', 'ws://localhost:8000/ws/chat')
USER_ID = os.getenv('DEMO_USER', 'demo-user-1')
MODEL = os.getenv('DEMO_MODEL', 'gemini-1.5-flash')
PROMPT = os.getenv('DEMO_PROMPT', "Write a short haiku about coding")

async def run():
    async with websockets.connect(SERVER) as ws:
        # Send initial chat message
        payload = {
            'type': 'chat',
            'prompt': PROMPT,
            'model': MODEL,
            'user_id': USER_ID,
        }
        await ws.send(json.dumps(payload))

        print('Sent prompt; awaiting stream...')
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                except Exception:
                    print('RAW:', message)
                    continue

                mtype = data.get('type')
                if mtype == 'chunk':
                    print(data.get('content'), end='', flush=True)
                elif mtype == 'done':
                    print('\n\n[Done]')
                    print(json.dumps(data, indent=2))
                    break
                elif mtype == 'error':
                    print('\n[Error]', data.get('error'), data.get('message'))
                    break
                else:
                    print('\n[Message]', data)
        except websockets.exceptions.ConnectionClosed as e:
            print('\nConnection closed:', e)

if __name__ == '__main__':
    asyncio.run(run())
