"""Reranker factory.

Reranking is switchable on/off and supports one or many chained cross-encoders,
configured via ``RAG_RERANK_ENABLED`` and ``RAG_RERANK_MODELS``. A per-request
override lets the UI toggle it live.
"""
from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import BaseReranker
from .rerankers import ChainReranker, CrossEncoderReranker, NoOpReranker


@lru_cache
def _build(enabled: bool, models: tuple[str, ...]) -> BaseReranker:
    if not enabled or not models:
        return NoOpReranker()
    encoders = [CrossEncoderReranker(m) for m in models]
    return encoders[0] if len(encoders) == 1 else ChainReranker(encoders)


def get_reranker(enabled: bool | None = None,
                 models: list[str] | None = None) -> BaseReranker:
    settings = get_settings()
    enabled = settings.rerank_enabled if enabled is None else enabled
    models = models if models is not None else settings.rerank_models
    return _build(bool(enabled), tuple(models))
