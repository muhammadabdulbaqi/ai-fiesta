"""
LLM Provider Factory

Returns a provider instance based on model name.
"""

from typing import Optional

from app.llm.base import BaseLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.mock import MockLLMProvider  # you may modify/remove this


class LLMProviderFactory:
    """
    Returns the correct provider based on the model name.
    """

    @staticmethod
    def create_provider(model: str) -> BaseLLMProvider:
        """
        Picks provider based on model string:
        - "gpt-4", "gpt-4o-mini", etc → OpenAI
        - "claude-3-pro", etc → Anthropic
        - "gemini-2.5-pro", "gemini-flash" → Gemini
        """
        model_lower = (model or "").lower()

        if any(key in model_lower for key in ["gpt", "o1-mini", "openai"]):
            return OpenAIProvider()

        if "claude" in model_lower:
            return AnthropicProvider()

        if "gemini" in model_lower:
            return GeminiProvider()

        # fallback
        return MockLLMProvider()

    @staticmethod
    def get_available_models() -> dict:
        """
        List supported models for each provider.
        """
        return {
            "openai": [
                "gpt-4o-mini",
                "gpt-4.1",
                "gpt-4o",
                "gpt-3.5-turbo",
            ],
            "anthropic": [
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229",
                "claude-3-opus-20240229",
            ],
            "gemini": [
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-pro-latest",
                "gemini-flash-latest",
            ],
            "mock": [
                "mock-gpt",
                "mock-claude",
            ],
        }


llm_factory = LLMProviderFactory()
