"""
Grok Provider (X.AI) - Implementation with BaseLLMProvider compliance.

Implements:
- generate()
- stream_generate()
- estimate_cost()
"""

from typing import AsyncIterator, Optional
import os

try:
    from openai import AsyncOpenAI
    OPENAI_PRESENT = True
except Exception:
    AsyncOpenAI = None
    OPENAI_PRESENT = False

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.utils.stream_emulation import emulate_stream_text
from app.config import settings


class GrokProvider(BaseLLMProvider):
    name = "grok"
    default_model = "grok-beta"

    def __init__(self, api_key: Optional[str] = None):
        # Grok uses OpenAI-compatible API
        self.api_key = api_key or getattr(settings, "grok_api_key", None) or os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise RuntimeError("GROK_API_KEY not configured.")
        
        self.provider_name = "grok"
        
        if not OPENAI_PRESENT:
            raise RuntimeError("openai SDK not installed. Install with: pip install openai")
        
        # Grok API endpoint
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        """Generate a full response using Grok API."""
        model = model or self.default_model
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            content = response.choices[0].message.content or ""
            
            return {
                "content": content,
                "model": getattr(response, "model", model),
                "prompt_tokens": getattr(response.usage, "prompt_tokens", token_counter.count_tokens(prompt, "openai")),
                "completion_tokens": getattr(response.usage, "completion_tokens", token_counter.count_tokens(content, "openai")),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }
        except Exception as e:
            raise RuntimeError(f"Grok API error: {str(e)}")

    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response from Grok API."""
        model = model or self.default_model
        
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
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except Exception as e:
            # Fallback to non-streaming
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get("content", "")
                if content:
                    async for part in emulate_stream_text(content):
                        yield part
            except Exception:
                raise RuntimeError(f"Grok streaming error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """Count tokens using OpenAI tokenizer (Grok is compatible)."""
        return token_counter.count_tokens(text, "openai")

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        """
        Grok pricing (per 1K tokens, approximate):
        Beta:  $1.00 input / $3.00 output
        Grok-2: $2.00 input / $6.00 output
        """
        model = model or self.default_model
        model_lower = model.lower()

        if "grok-2" in model_lower or "grok2" in model_lower:
            input_rate = 2.00 / 1000
            output_rate = 6.00 / 1000
        else:
            input_rate = 1.00 / 1000
            output_rate = 3.00 / 1000

        input_cost = prompt_tokens * input_rate
        output_cost = completion_tokens * output_rate

        return input_cost + output_cost

