"""Vector store factory."""
from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import BaseVectorStore


@lru_cache
def get_vectorstore() -> BaseVectorStore:
    settings = get_settings()
    if settings.vectorstore_provider == "chroma":
        from .chroma_store import ChromaVectorStore
        return ChromaVectorStore()
    raise ValueError(f"Unknown vector store: {settings.vectorstore_provider}")
