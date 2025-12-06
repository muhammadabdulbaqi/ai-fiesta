from typing import Optional, AsyncIterator
import os

from app.llm.base import BaseLLMProvider
from app.utils.token_counter import token_counter

try:
    import google.generativeai as genai
except Exception:
    genai = None


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if genai is not None and api_key:
            try:
                genai.configure(api_key=api_key)
            except Exception:
                pass
        self.provider_name = "gemini"

    async def generate(self, prompt: str, model: str = "gemini-2.5-pro", max_tokens: int = 1000, temperature: float = 0.7) -> dict:
        if genai is None:
            raise Exception("Google generativeai library not available")
        try:
            model_instance = genai.GenerativeModel(model)
            generation_config = {"temperature": temperature, "max_output_tokens": max_tokens}
            response = await model_instance.generate_content_async(prompt, generation_config=generation_config)
            prompt_tokens = self.count_tokens(prompt)
            
            # Handle response.parts (Gemini may return structured responses, not just text)
            completion_text = ""
            if hasattr(response, "text"):
                try:
                    completion_text = response.text
                except Exception:
                    # If .text accessor fails, extract from parts
                    if hasattr(response, "parts") and response.parts:
                        for part in response.parts:
                            if hasattr(part, "text"):
                                completion_text += part.text
            
            completion_tokens = self.count_tokens(completion_text)
            return {
                "content": completion_text,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    async def stream_generate(self, prompt: str, model: str = "gemini-2.5-pro", max_tokens: int = 1000, temperature: float = 0.7) -> AsyncIterator[str]:
        if genai is None:
            raise Exception("Google generativeai library not available")
        try:
            model_instance = genai.GenerativeModel(model)
            generation_config = {"temperature": temperature, "max_output_tokens": max_tokens}
            response = await model_instance.generate_content_async(prompt, generation_config=generation_config, stream=True)
            async for chunk in response:
                if getattr(chunk, "text", None):
                    yield chunk.text
        except Exception as e:
            raise Exception(f"Gemini streaming error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        return token_counter.count_tokens(text, "gemini")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Estimate cost. Use slightly cheaper rates for 'flash' models.

        Rates (per 1K tokens):
        - flash: input $0.00015, output $0.0003
        - pro (default): input $0.00025, output $0.0005
        """
        model_lower = (model or "").lower()
        if "flash" in model_lower:
            input_rate = 0.00015
            output_rate = 0.0003
        else:
            input_rate = 0.00025
            output_rate = 0.0005

        input_cost = (prompt_tokens / 1000) * input_rate
        output_cost = (completion_tokens / 1000) * output_rate
        return input_cost + output_cost
