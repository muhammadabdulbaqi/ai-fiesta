from typing import Optional

from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .mock import MockLLMProvider


class LLMProviderFactory:
    @staticmethod
    def create_provider(model: str) -> BaseLLMProvider:
        model_lower = (model or "").lower()
        if any(name in model_lower for name in ["gpt", "turbo"]):
            return OpenAIProvider()
        elif "claude" in model_lower:
            return AnthropicProvider()
        elif "gemini" in model_lower:
            return GeminiProvider()
        elif "mock" in model_lower or not model_lower:
            return MockLLMProvider()
        else:
            # default to mock if unknown
            return MockLLMProvider()

    @staticmethod
    def get_available_models() -> dict:
        # Updated model lists based on `api_test_results.json`
        return {
            "openai": [
                "gpt-4-0613",
                "gpt-4",
                "gpt-3.5-turbo",
                "gpt-5.1-codex-max",
                "gpt-5.1-2025-11-13",
                "gpt-5.1",
                "gpt-5.1-codex",
                "gpt-5.1-codex-mini",
                "gpt-3.5-turbo-instruct",
                "gpt-3.5-turbo-0125",
                "gpt-4-turbo",
                "gpt-4o",
                "gpt-4.1",
                "gpt-5",
                "gpt-3.5-turbo-16k",
            ],
            "anthropic": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            "gemini": [
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-2.0-pro-exp",
                "gemini-pro-latest",
                "gemini-flash-latest",
            ],
            "mock": ["mock-gpt4", "mock-claude"],
        }


llm_factory = LLMProviderFactory()
