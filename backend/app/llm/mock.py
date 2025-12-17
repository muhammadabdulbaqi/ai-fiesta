from .base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Simple mock LLM provider for testing without external APIs."""

    def generate(self, prompt: str, model: str = "mock") -> tuple[str, int]:
        # Very simple echo response and token counting
        response = f"Mock response: {prompt}"
        tokens = self.count_tokens(response)
        return response, tokens

    def count_tokens(self, text: str) -> int:
        # Naive token counting: whitespace-separated words
        return max(1, len(text.split()))

    def estimate_cost(self, tokens: int) -> float:
        # Fake cost model
        return tokens * 0.0001
