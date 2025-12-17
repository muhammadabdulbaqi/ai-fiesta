"""
Perplexity Provider - Implementation with BaseLLMProvider compliance.

Implements:
- generate()
- stream_generate()
- estimate_cost()
"""

from typing import AsyncIterator, Optional
import os
import json

try:
    import httpx
    HTTPX_PRESENT = True
except Exception:
    httpx = None
    HTTPX_PRESENT = False

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.utils.stream_emulation import emulate_stream_text
from app.config import settings


class PerplexityProvider(BaseLLMProvider):
    name = "perplexity"
    default_model = "perplexity-sonar"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "perplexity_api_key", None) or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise RuntimeError("PERPLEXITY_API_KEY not configured.")
        
        self.provider_name = "perplexity"
        
        if not HTTPX_PRESENT:
            raise RuntimeError("httpx not installed. Install with: pip install httpx")
        
        self.base_url = "https://api.perplexity.ai"

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model name to Perplexity API model."""
        model = model or self.default_model
        model_lower = model.lower()
        
        # Map our model names to Perplexity API model names
        if "sonar-pro" in model_lower or "sonarpro" in model_lower:
            return "sonar-pro"
        elif "sonar" in model_lower:
            return "sonar"
        else:
            return "sonar"  # Default

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        """Generate a full response using Perplexity API."""
        actual_model = self._resolve_model(model)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": actual_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                
                return {
                    "content": content,
                    "model": data.get("model", actual_model),
                    "prompt_tokens": usage.get("prompt_tokens", token_counter.count_tokens(prompt, "openai")),
                    "completion_tokens": usage.get("completion_tokens", token_counter.count_tokens(content, "openai")),
                    "total_tokens": usage.get("total_tokens", 0),
                }
            except Exception as e:
                raise RuntimeError(f"Perplexity API error: {str(e)}")

    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response from Perplexity API."""
        actual_model = self._resolve_model(model)
        
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": actual_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True,
                    },
                    timeout=60.0,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                # Fallback to non-streaming
                try:
                    result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                    content = result.get("content", "")
                    if content:
                        async for part in emulate_stream_text(content):
                            yield part
                except Exception:
                    raise RuntimeError(f"Perplexity streaming error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """Count tokens using OpenAI tokenizer (Perplexity is compatible)."""
        return token_counter.count_tokens(text, "openai")

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        """
        Perplexity pricing (per 1K tokens, approximate):
        Sonar: $0.50 input / $2.00 output
        Sonar Pro: $1.00 input / $4.00 output
        """
        model = model or self.default_model
        model_lower = model.lower()

        if "sonar-pro" in model_lower or "sonarpro" in model_lower:
            input_rate = 1.00 / 1000
            output_rate = 4.00 / 1000
        else:
            input_rate = 0.50 / 1000
            output_rate = 2.00 / 1000

        input_cost = prompt_tokens * input_rate
        output_cost = completion_tokens * output_rate

        return input_cost + output_cost

