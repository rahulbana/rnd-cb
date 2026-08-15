"""Embedding provider factory."""
from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import BaseEmbedder


@lru_cache
def get_embedder() -> BaseEmbedder:
    settings = get_settings()
    if settings.embedding_provider == "sentence_transformer":
        from .sentence_transformer import SentenceTransformerEmbedder
        return SentenceTransformerEmbedder(settings.embedding_model)
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
