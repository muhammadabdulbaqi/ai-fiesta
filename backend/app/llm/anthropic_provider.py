from typing import Optional, AsyncIterator
import os
import asyncio

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.utils.stream_emulation import emulate_stream_text

try:
    from anthropic import AsyncAnthropic
except Exception:
    AsyncAnthropic = None


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = AsyncAnthropic(api_key=api_key) if AsyncAnthropic is not None else None
        self.provider_name = "anthropic"

    async def generate(self, prompt: str, model: str = "claude-3-haiku-20240307", max_tokens: int = 1000, temperature: float = 0.7) -> dict:
        if self.client is None:
            raise Exception("Anthropic client not available (library not installed)")
        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return {
                "content": response.content[0].text if hasattr(response, 'content') else getattr(response, 'text', ""),
                "model": getattr(response, "model", model),
                "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                "completion_tokens": getattr(response.usage, "output_tokens", 0),
                "total_tokens": getattr(response.usage, "input_tokens", 0) + getattr(response.usage, "output_tokens", 0),
            }
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    async def stream_generate(self, prompt: str, model: str = "claude-3-haiku-20240307", max_tokens: int = 1000, temperature: float = 0.7) -> AsyncIterator[str]:
        if self.client is None:
            raise Exception("Anthropic client not available (library not installed)")
        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception:
            # Fallback to non-streaming generate and emulate streaming
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content', '') if isinstance(result, dict) else str(result)
                async for part in emulate_stream_text(content):
                    yield part
            except Exception:
                return

    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "anthropic")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        prices = {
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
        }
        base_model = "claude-3-haiku"
        for key in prices.keys():
            if key in model:
                base_model = key
                break
        pricing = prices[base_model]
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
