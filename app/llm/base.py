from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    Provides both synchronous-like (awaitable) full-response generation and
    async streaming generation. Providers should implement both so callers can
    choose the appropriate mode.
    """

    @abstractmethod
    async def generate(self, prompt: str, model: str = "mock", **kwargs) -> dict:
        """Asynchronously generate a full response for the given prompt.

        Returns a dict with at least: {
            "content": str,
            "model": str,
            "prompt_tokens": int,
            "completion_tokens": int,
            "total_tokens": int,
        }
        """

    @abstractmethod
    async def stream_generate(self, prompt: str, model: str = "mock", **kwargs) -> AsyncIterator[str]:
        """Asynchronously stream the response. Yields string chunks as they arrive."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Return token count for a given text"""

    @abstractmethod
    def estimate_cost(self, *args, **kwargs) -> float:
        """Estimate cost for a request. Signature left generic for provider flexibility."""
