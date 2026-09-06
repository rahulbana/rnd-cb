"""Cohere Rerank adapter -- hosted reranking behind the same port."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


class CohereReranker:
    """Re-scores candidates via the Cohere Rerank API."""

    name = "cohere"

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self.model = model
        self._client: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> CohereReranker:
        return cls(api_key=settings.COHERE_API_KEY, model=settings.COHERE_RERANK_MODEL)

    def _get_client(self) -> Any:
        if self._client is None:
            import cohere  # lazy import

            self._client = cohere.Client(api_key=self._api_key)
        return self._client

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
        *,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        documents = [c.chunk.text for c in candidates]
        response = self._get_client().rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=min(top_k, len(documents)),
        )
        results: list[RetrievedChunk] = []
        for item in response.results:
            base = candidates[item.index]
            results.append(
                RetrievedChunk(
                    chunk=base.chunk,
                    score=float(item.relevance_score),
                    source="reranker",
                )
            )
        return results
