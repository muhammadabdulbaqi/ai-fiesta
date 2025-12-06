"""
Minimal Google Gemini 2.5 provider.

Key points:
- Resolves friendly model names (e.g. "gemini-2.5-flash") to the API form "models/gemini-2.5-flash".
- Extracts text only from candidates -> content -> parts (the correct shape for Gemini 2.5).
- Implements `generate` and `stream_generate` (async) and `count_tokens`.
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
        if not GENAI_PRESENT:
            raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")

        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not configured in environment or settings")

        genai.configure(api_key=self.api_key)

    def _resolve_model(self, model: Optional[str]) -> str:
        if not model:
            model = self.default_model
        if model.startswith("models/"):
            return model
        return f"models/{model}"

    def _extract_from_candidates(self, obj) -> str:
        parts = []
        if not hasattr(obj, "candidates"):
            return ""
        for cand in obj.candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue
            if not getattr(content, "parts", None):
                continue
            for part in content.parts:
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)
        return "".join(parts)

    async def generate(self, prompt: str, model: Optional[str] = None, max_tokens: int = 1024, temperature: float = 0.7) -> dict:
        actual = self._resolve_model(model)
        model_obj = genai.GenerativeModel(model_name=actual)

        try:
            response = await model_obj.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(max_output_tokens=max_tokens, temperature=temperature),
            )
        except Exception as e:
            msg = str(e) or repr(e)
            if google_exceptions and isinstance(e, google_exceptions.NotFound):
                raise RuntimeError(f"Gemini model not found: {actual}. Run genai.list_models() to inspect available models. {msg}")
            raise RuntimeError(f"Gemini generate error: {msg}")

        text = self._extract_from_candidates(response)
        prompt_tokens = token_counter.count_tokens(prompt, "gemini")
        completion_tokens = token_counter.count_tokens(text, "gemini")
        return {
            "content": text,
            "model": actual,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    async def stream_generate(self, prompt: str, model: Optional[str] = None, max_tokens: int = 1024, temperature: float = 0.7) -> AsyncIterator[str]:
        actual = self._resolve_model(model)
        model_obj = genai.GenerativeModel(model_name=actual)

        try:
            stream = await model_obj.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(max_output_tokens=max_tokens, temperature=temperature),
                stream=True,
            )
        except Exception as e:
            msg = str(e) or repr(e)
            if google_exceptions and isinstance(e, google_exceptions.NotFound):
                raise RuntimeError(f"Gemini model not found: {actual}. Run genai.list_models() to inspect available models. {msg}")
            raise RuntimeError(f"Gemini streaming error: {msg}")

        async for chunk in stream:
            text = self._extract_from_candidates(chunk)
            if text:
                yield text

    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "gemini")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: Optional[str] = None) -> float:
        model_lower = (model or "").lower() if model else ""
        if "flash" in model_lower:
            input_rate = 0.075 / 1000
            output_rate = 0.30 / 1000
        else:
            input_rate = 1.25 / 1000
            output_rate = 5.00 / 1000
        return (prompt_tokens / 1000) * input_rate + (completion_tokens / 1000) * output_rate