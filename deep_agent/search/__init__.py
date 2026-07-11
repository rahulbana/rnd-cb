"""Switchable web-search provider layer."""

from deep_agent.search.base import SearchClient
from deep_agent.search.factory import get_search_client

__all__ = ["SearchClient", "get_search_client"]
