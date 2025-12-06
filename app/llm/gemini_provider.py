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

        # provider_name expected by other modules
        self.provider_name = "gemini"

        genai.configure(api_key=self.api_key)
        # allow forcing non-streaming via env or settings
        self.force_non_streaming = bool(getattr(settings, "GEMINI_FORCE_NON_STREAMING", False) or os.getenv("GEMINI_FORCE_NON_STREAMING", "").lower() in ("1","true","yes"))
        # Try to auto-detect a usable Gemini model (generate-capable)
        self.auto_model_actual: Optional[str] = None
        try:
            models = genai.list_models()
            # models can be a sequence of objects or dicts
            # Preferred order (user-specified): flash, pro, 2.0-flash
            preferred = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]

            # Build a set of available model base names -> full API name mapping
            available = {}
            for m in models:
                name = getattr(m, 'name', None) or (m.get('name') if isinstance(m, dict) else None)
                if not name:
                    name = str(m)
                base = name.split('/')[-1] if '/' in name else name
                available[base] = name if name.startswith('models/') else f'models/{name}'

            # Choose first preferred that exists
            for pref in preferred:
                if pref in available:
                    self.auto_model_actual = available[pref]
                    break

            # fallback: pick any gemini model if not set
            if not self.auto_model_actual:
                for base, full in available.items():
                    if base and base.startswith('gemini'):
                        self.auto_model_actual = full
                        break
        except Exception:
            # ignore errors here — we'll surface errors at call-time
            self.auto_model_actual = None

    def _resolve_model(self, model: Optional[str]) -> str:
        # If explicit model provided, resolve to API form
        if model:
            return model if model.startswith("models/") else f"models/{model}"

        # No explicit model: prefer auto-detected model then default
        if getattr(self, 'auto_model_actual', None):
            return self.auto_model_actual
        return self.default_model if self.default_model.startswith('models/') else f"models/{self.default_model}"

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
            is_not_found = False
            try:
                if google_exceptions and isinstance(e, google_exceptions.NotFound):
                    is_not_found = True
            except Exception:
                is_not_found = False
            # Also detect 'not found' or 404 text in the message as NotFound
            if not is_not_found and isinstance(msg, str) and ("not found" in msg.lower() or "404" in msg.lower() or "is not found" in msg.lower()):
                is_not_found = True
            if is_not_found:
                # Try fallback to auto-detected model if available
                if getattr(self, 'auto_model_actual', None) and self.auto_model_actual != actual:
                    try:
                        response = await genai.GenerativeModel(model_name=self.auto_model_actual).generate_content_async(
                            prompt,
                            generation_config=genai.GenerationConfig(max_output_tokens=max_tokens, temperature=temperature),
                        )
                    except Exception as e2:
                        raise RuntimeError(f"Gemini generate error (tried fallback {self.auto_model_actual}): {str(e2) or repr(e2)}")
                else:
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

        # If explicitly forced to non-streaming, yield the non-streaming result and return.
        if getattr(self, 'force_non_streaming', False):
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                content = result.get('content', '')
                if content:
                    yield content
            except Exception:
                # swallow errors for streaming callers — do not raise
                return
            return
        try:
            stream = await model_obj.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(max_output_tokens=max_tokens, temperature=temperature),
                stream=True,
            )
        except Exception as e:
            # If streaming creation failed (NotFound or other), try fallback to auto-detected model
            msg = str(e) or repr(e)
            is_not_found = False
            try:
                if google_exceptions and isinstance(e, google_exceptions.NotFound):
                    is_not_found = True
            except Exception:
                is_not_found = False
            if not is_not_found and isinstance(msg, str) and ("not found" in msg.lower() or "404" in msg.lower() or "is not found" in msg.lower()):
                is_not_found = True

            if is_not_found and getattr(self, 'auto_model_actual', None) and self.auto_model_actual != actual:
                try:
                    stream = await genai.GenerativeModel(model_name=self.auto_model_actual).generate_content_async(
                        prompt,
                        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens, temperature=temperature),
                        stream=True,
                    )
                except Exception:
                    # fallback to non-streaming generate; swallow any errors
                    try:
                        result = await self.generate(prompt=prompt, model=self.auto_model_actual, max_tokens=max_tokens, temperature=temperature)
                        yield result.get('content', '')
                    except Exception:
                        return
                    return
            else:
                # For other errors, try non-streaming generate as a graceful fallback and swallow errors
                try:
                    result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                    yield result.get('content', '')
                    return
                except Exception:
                    return

        # Iterate stream; guard against StopAsyncIteration or unexpected errors during iteration
        try:
            async for chunk in stream:
                try:
                    text = self._extract_from_candidates(chunk)
                except Exception:
                    text = ""
                if text:
                    yield text
        except StopAsyncIteration:
            # Stream ended unexpectedly; attempt a final non-streaming generate as fallback and swallow errors
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                if result and result.get('content'):
                    yield result.get('content')
            except Exception:
                return
        except Exception:
            # On any other iteration error, try non-streaming generate once and swallow errors
            try:
                result = await self.generate(prompt=prompt, model=model, max_tokens=max_tokens, temperature=temperature)
                yield result.get('content', '')
            except Exception:
                return

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