"""
LLM Provider Factory

Returns a provider instance based on model name.
"""

from typing import Optional

from app.llm.base import BaseLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.grok_provider import GrokProvider
from app.llm.perplexity_provider import PerplexityProvider
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

        if any(key in model_lower for key in ["gpt", "o1", "openai"]):
            return OpenAIProvider()

        if "claude" in model_lower:
            return AnthropicProvider()

        if "gemini" in model_lower:
            return GeminiProvider()

        if "grok" in model_lower:
            return GrokProvider()

        if "perplexity" in model_lower or "sonar" in model_lower:
            return PerplexityProvider()

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
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "o1-mini",
                "o1-preview",
            ],
            "anthropic": [
                "claude-3-haiku-20240307",
                "claude-3-5-haiku-20241022",
                "claude-3-sonnet-20240229",
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229",
            ],
            "gemini": [
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro-latest",
                "gemini-flash-latest",
            ],
            "grok": [
                "grok-beta",
                "grok-2",
            ],
            "perplexity": [
                "perplexity-sonar",
                "perplexity-sonar-pro",
            ],
            "mock": [
                "mock-gpt",
                "mock-claude",
            ],
        }


llm_factory = LLMProviderFactory()
