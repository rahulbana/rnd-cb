"""Select an LLM provider by name.

To add a new vendor, implement :class:`LLMProvider` and register it here (or
call :func:`register_provider`). Agents need no changes.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from .base import LLMProvider

# name -> builder(model, api_key, **kwargs) -> LLMProvider
_REGISTRY: Dict[str, Callable[..., LLMProvider]] = {}


def register_provider(name: str, builder: Callable[..., LLMProvider]) -> None:
    """Register a custom provider builder under ``name``."""
    _REGISTRY[name.lower()] = builder


def get_llm_provider(
    name: str = "openai",
    *,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """Return an initialised LLM provider.

    ``name`` defaults to ``"openai"``. ``model`` overrides the provider's
    default model when given.
    """
    key = name.lower()

    if key in _REGISTRY:
        return _REGISTRY[key](model=model, api_key=api_key, **kwargs)

    if key == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model=model or "gpt-4o", api_key=api_key, **kwargs)

    raise ValueError(
        f"Unknown LLM provider: {name!r}. Built-in: 'openai'. "
        "Register others with register_provider()."
    )
