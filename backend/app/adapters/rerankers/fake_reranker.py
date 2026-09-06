"""In-memory fake reranker -- scores by query-term overlap."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


class FakeReranker:
    """Deterministic lexical-overlap reranker, no model or network."""

    name = "fake"

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeReranker:
        return cls()

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        terms = {t.lower() for t in query.split() if t}

        def overlap(rc: RetrievedChunk) -> float:
            words = {w.lower() for w in rc.chunk.text.split()}
            if not terms:
                return 0.0
            return len(terms & words) / len(terms)

        rescored = [
            RetrievedChunk(chunk=rc.chunk, score=overlap(rc), source="reranker")
            for rc in candidates
        ]
        rescored.sort(key=lambda rc: rc.score, reverse=True)
        return rescored[:top_k]
