"""Local cross-encoder reranker (default).

A cross-encoder scores (query, passage) pairs jointly, which is far more precise
than the bi-encoder similarity used for first-stage retrieval -- but too slow to
run over the whole corpus, so it re-scores only the retrieved candidates. The
model (torch) loads lazily on first use.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


class CrossEncoderReranker:
    """Re-scores candidates with a sentence-transformers CrossEncoder."""

    name = "cross_encoder"

    def __init__(self, model: str) -> None:
        self.model = model
        self._encoder: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> CrossEncoderReranker:
        return cls(model=settings.RERANK_MODEL)

    def _get_encoder(self) -> Any:
        if self._encoder is None:
            from sentence_transformers import CrossEncoder  # lazy import

            self._encoder = CrossEncoder(self.model)
        return self._encoder

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [[query, c.chunk.text] for c in candidates]
        scores = self._get_encoder().predict(pairs)
        rescored = [
            RetrievedChunk(chunk=c.chunk, score=float(s), source="reranker")
            for c, s in zip(candidates, scores, strict=True)
        ]
        rescored.sort(key=lambda rc: rc.score, reverse=True)
        return rescored[:top_k]
