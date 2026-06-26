"""Registry/factory for LLM providers.

Register additional vendors here (Anthropic, Azure, Bedrock, ...) without
touching the agent code.
"""
from __future__ import annotations

from typing import Callable, Dict

from ...core.config import Settings
from ...core.exceptions import ConfigurationError
from .base import BaseLLMProvider
from .openai_provider import OpenAILLMProvider

# provider name -> builder(settings) -> BaseLLMProvider
_REGISTRY: Dict[str, Callable[[Settings], BaseLLMProvider]] = {
    "openai": OpenAILLMProvider,
}


def register_llm_provider(
    name: str, builder: Callable[[Settings], BaseLLMProvider]
) -> None:
    _REGISTRY[name.lower()] = builder


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    name = settings.llm_provider.lower()
    builder = _REGISTRY.get(name)
    if builder is None:
        raise ConfigurationError(
            f"Unknown LLM provider '{name}'. Available: {sorted(_REGISTRY)}"
        )
    return builder(settings)
