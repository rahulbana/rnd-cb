"""Registry/factory for search providers."""
from __future__ import annotations

from typing import Callable, Dict

from ...core.config import Settings
from ...core.exceptions import ConfigurationError
from .base import BaseSearchProvider
from .duckduckgo import DuckDuckGoSearchProvider
from .tavily import TavilySearchProvider

# provider name -> builder(settings) -> BaseSearchProvider
_REGISTRY: Dict[str, Callable[[Settings], BaseSearchProvider]] = {
    "tavily": TavilySearchProvider,
    "duckduckgo": DuckDuckGoSearchProvider,
}


def register_search_provider(
    name: str, builder: Callable[[Settings], BaseSearchProvider]
) -> None:
    _REGISTRY[name.lower()] = builder


def get_search_provider(settings: Settings) -> BaseSearchProvider:
    name = settings.resolved_search_provider
    builder = _REGISTRY.get(name)
    if builder is None:
        raise ConfigurationError(
            f"Unknown search provider '{name}'. Available: {sorted(_REGISTRY)}"
        )
    return builder(settings)
