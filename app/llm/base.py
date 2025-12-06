from abc import ABC, abstractmethod
from typing import Tuple


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, model: str = "mock") -> Tuple[str, int]:
        """Generate a response for the given prompt.

        Returns a tuple of (response_text, tokens_used)
        """

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Return token count for a given text"""

    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for a number of tokens"""
