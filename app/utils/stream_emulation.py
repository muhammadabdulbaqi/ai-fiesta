import asyncio
from typing import AsyncIterator

async def emulate_stream_text(text: str, chunk_size: int = 120, delay: float = 0.02) -> AsyncIterator[str]:
    """Asynchronously yield `text` in chunks with a small delay between them.

    - `chunk_size`: number of characters per emitted chunk.
    - `delay`: seconds to await between chunks (can be 0 for immediate emission).

    Use this when a provider does not support streaming; it provides a smooth, client-friendly streamed experience.
    """
    if not text:
        return
    pos = 0
    L = len(text)
    while pos < L:
        end = min(pos + chunk_size, L)
        yield text[pos:end]
        pos = end
        if pos < L:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
