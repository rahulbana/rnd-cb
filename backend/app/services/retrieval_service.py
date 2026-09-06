"""Retrieval orchestration -- retrieve then rerank, over injected ports."""

from __future__ import annotations

from app.domain.interfaces import Reranker, Retriever
from app.domain.models import RetrievedChunk


class RetrievalService:
    """Coordinates retrieval + reranking. Query understanding lands in Phase 5."""

    def __init__(self, retriever: Retriever, reranker: Reranker) -> None:
        self._retriever = retriever
        self._reranker = reranker

    async def search(
        self, query: str, *, namespace: str, top_k: int = 5, fetch_k: int = 20
    ) -> list[RetrievedChunk]:
        candidates = await self._retriever.retrieve(
            query, namespace=namespace, top_k=fetch_k
        )
        return await self._reranker.rerank(query, candidates, top_k=top_k)
