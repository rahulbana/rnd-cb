"""Reranker port -- re-scores retrieved candidates for relevance."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class Reranker(Protocol):
    """Any reranking backend must satisfy this."""

    name: str  # "cross_encoder" | "cohere" | "llm" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> Reranker:
        """Construct the adapter from application settings."""
        ...

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return the ``top_k`` candidates, re-scored and re-ordered."""
        ...
