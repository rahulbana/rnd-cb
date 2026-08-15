"""Retriever factory. Strategy is switchable per-request or via config."""
from __future__ import annotations

from ..config import get_settings
from .base import BaseRetriever


def get_retriever(strategy: str | None = None) -> BaseRetriever:
    strategy = strategy or get_settings().retrieval_strategy
    if strategy == "simple":
        from .simple import SimpleRetriever
        return SimpleRetriever()
    if strategy == "hybrid":
        from .hybrid import HybridRetriever
        return HybridRetriever()
    raise ValueError(f"Unknown retrieval strategy: {strategy}")
