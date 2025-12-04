from typing import Optional
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

def get_provider(provider_name: str, **kwargs) -> LLMProvider:
    """
    Factory function to get an LLM provider instance.

    Args:
        provider_name: The name of the provider ("openai" or "anthropic").
        **kwargs: Arguments to pass to the provider constructor.

    Returns:
        An instance of LLMProvider.

    Raises:
        ValueError: If the provider name is not supported.
    """
    if provider_name.lower() == "openai":
        return OpenAIProvider(**kwargs)
    elif provider_name.lower() == "anthropic":
        return AnthropicProvider(**kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
