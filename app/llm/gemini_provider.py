"""
Gemini Provider – Correct implementation with full BaseLLMProvider compliance.

Implements:
- generate()
- stream_generate()    <-- required by BaseLLMProvider
- estimate_cost()      <-- required by BaseLLMProvider
"""

from typing import AsyncIterator, Optional
import os

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GENAI_PRESENT = True
except Exception:
    genai = None
    google_exceptions = None
    GENAI_PRESENT = False

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter
from app.config import settings


class GeminiProvider(BaseLLMProvider):
    name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        # Read API key from explicit arg, settings, or environment.
        self.api_key = api_key or getattr(settings, "gemini_api_key", None) or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not configured.")
        # Public provider identifier used by tracking and analytics
        self.provider_name = "gemini"
        if not GENAI_PRESENT:
            raise RuntimeError("google-generativeai SDK not installed. Install with: pip install google-generativeai google-api-core")

        genai.configure(api_key=self.api_key)

    # -----------------------------------------------------
    # Model Resolution
    # -----------------------------------------------------
    def _resolve_model(self, model: Optional[str]) -> str:
        """Convert 'gemini-2.5-flash' → 'models/gemini-2.5-flash'."""
        if not model:
            model = self.default_model

        if model.startswith("models/"):
            return model

        return f"models/{model}"

    # -----------------------------------------------------
    # Response Extraction
    # -----------------------------------------------------
    def _extract_text(self, obj) -> str:
        """Extract text from Gemini objects (stream or non-stream)."""
        if not hasattr(obj, "candidates"):
            return ""

        parts = []
        for cand in obj.candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue

            for part in getattr(content, "parts", []):
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)

        return "".join(parts).strip()

    # -----------------------------------------------------
    # Non-Streaming Generate
    # -----------------------------------------------------
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:

        actual = self._resolve_model(model)
        model_obj = genai.GenerativeModel(actual)

        response = await model_obj.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )

        text = self._extract_text(response)

        return {
            "content": text,
            "model": actual,
            "prompt_tokens": token_counter.count_tokens(prompt, "gemini"),
            "completion_tokens": token_counter.count_tokens(text, "gemini"),
        }

    # -----------------------------------------------------
    # Streaming Generate (BaseLLMProvider requirement)
    # -----------------------------------------------------
    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[str]:

        actual = self._resolve_model(model)
        model_obj = genai.GenerativeModel(actual)

        try:
            stream = await model_obj.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
                stream=True,
            )
        except Exception as e:
            # If this looks like a quota or rate-limit error, surface a clearer message
            msg = str(e)
            lower = msg.lower()
            if "quota" in lower or "limit" in lower or "rate" in lower or "exhausted" in lower:
                raise RuntimeError(f"Gemini quota/rate error: {msg}")

            # Otherwise fallback to non-streaming result to preserve UX
            result = await self.generate(prompt, actual, max_tokens, temperature)
            yield result["content"]
            return

        async for chunk in stream:
            text = self._extract_text(chunk)
            if text:
                yield text

    # -----------------------------------------------------
    # Token Counter Passthrough
    # -----------------------------------------------------
    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "gemini")

    # -----------------------------------------------------
    # Cost Estimation (required by BaseLLMProvider)
    # -----------------------------------------------------
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        """
        Gemini pricing (per 1K tokens):
        Flash:  $0.075 input / $0.30 output
        Pro:    $1.25 input / $5.00 output
        """
        model = model or self.default_model
        model_lower = model.lower()

        if "flash" in model_lower:
            input_rate = 0.075 / 1000
            output_rate = 0.30 / 1000
        else:
            input_rate = 1.25 / 1000
            output_rate = 5.00 / 1000

        input_cost = prompt_tokens * input_rate
        output_cost = completion_tokens * output_rate

        return input_cost + output_cost
