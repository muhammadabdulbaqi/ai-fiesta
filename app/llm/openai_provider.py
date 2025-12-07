from typing import Optional, AsyncIterator
import os
import asyncio

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.utils.stream_emulation import emulate_stream_text

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider with basic async support"""

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if AsyncOpenAI is not None else None
        self.provider_name = "openai"

    async def generate(self,
                      prompt: str,
                      model: str = "gpt-3.5-turbo",
                      max_tokens: int = 1000,
                      temperature: float = 0.7) -> dict:
        if self.client is None:
            raise Exception("OpenAI client not available (library not installed)")
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {
                "content": response.choices[0].message.content,
                "model": getattr(response, "model", model),
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def stream_generate(self, prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1000, temperature: float = 0.7) -> AsyncIterator[str]:
        if self.client is None:
            raise Exception("OpenAI client not available (library not installed)")
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    yield delta.content
        except Exception:
            # Streaming not available or failed — fallback to non-streaming generate
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content', '') if isinstance(result, dict) else str(result)
                # Emulate streaming by chunking the final content
                async for part in emulate_stream_text(content):
                    yield part
            except Exception:
                # swallow errors to avoid crashing the SSE handler
                return

    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "openai")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        prices = {
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        }
        pricing = prices.get(model, prices["gpt-3.5-turbo"])
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
