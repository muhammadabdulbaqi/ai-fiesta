"""Token counting utilities for different LLM providers"""
from typing import Literal, List
try:
    import tiktoken
except Exception:
    tiktoken = None

ProviderType = Literal["openai", "anthropic", "gemini"]


class TokenCounter:
    """Count tokens for different LLM providers"""

    def __init__(self):
        # OpenAI uses tiktoken if available
        self.openai_encoding = None
        if tiktoken is not None:
            try:
                self.openai_encoding = tiktoken.encoding_for_model("gpt-4")
            except Exception:
                self.openai_encoding = None

    def count_tokens(self, text: str, provider: ProviderType) -> int:
        if provider == "openai":
            if self.openai_encoding is not None:
                try:
                    return len(self.openai_encoding.encode(text))
                except Exception:
                    pass
            # fallback approximate
            return max(1, len(text.split()))

        elif provider == "anthropic":
            # Anthropic approximate: use same as openai if available
            if self.openai_encoding is not None:
                try:
                    return len(self.openai_encoding.encode(text))
                except Exception:
                    pass
            return max(1, len(text.split()))

        elif provider == "gemini":
            # Gemini: approximate as 1 token ≈ 4 chars
            return max(1, len(text) // 4)

        else:
            return max(1, len(text) // 4)

    def estimate_tokens(self, prompt: str, provider: ProviderType,
                        max_completion_tokens: int = 1000) -> dict:
        prompt_tokens = self.count_tokens(prompt, provider)
        return {
            "prompt_tokens": prompt_tokens,
            "max_completion_tokens": max_completion_tokens,
            "estimated_total": prompt_tokens + max_completion_tokens,
        }


# Global instance
token_counter = TokenCounter()
