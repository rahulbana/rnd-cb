"""Registry of available LLM providers.

Built-in providers register themselves on import (see ``providers.py``).
Third-party code can add its own by calling :func:`register_provider`.
"""
from __future__ import annotations

from deep_agent.llm.base import LLMProviderSpec

_REGISTRY: dict[str, LLMProviderSpec] = {}


def register_provider(spec_cls: type[LLMProviderSpec]) -> type[LLMProviderSpec]:
    """Class decorator that instantiates and registers a provider spec."""

    spec = spec_cls()
    if not spec.name:
        raise ValueError(f"{spec_cls.__name__} must define a non-empty 'name'.")
    _REGISTRY[spec.name.lower()] = spec
    return spec_cls


def get_provider(name: str) -> LLMProviderSpec:
    """Return the registered provider spec for ``name``.

    Raises a clear error listing the available providers when unknown.
    """

    key = (name or "").strip().lower()
    try:
        return _REGISTRY[key]
    except KeyError:
        raise ValueError(
            f"Unknown LLM provider '{name}'. Available: "
            f"{', '.join(available_providers())}. Register a custom provider "
            "with deep_agent.llm.register_provider()."
        ) from None


def available_providers() -> list[str]:
    """Return the sorted names of all registered providers."""

    return sorted(_REGISTRY)
