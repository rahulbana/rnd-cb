"""Hybrid retriever -- dense + sparse fused with Reciprocal Rank Fusion.

RRF combines rankings without needing score calibration between retrievers:
each candidate scores ``sum(1 / (k + rank))`` across the retrievers that
returned it. Robust and parameter-light; ``k`` dampens the weight of low ranks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.adapters.retrievers.dense_retriever import DenseRetriever
from app.adapters.retrievers.sparse_retriever import SparseRetriever
from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.domain.interfaces import Retriever


class HybridRetriever:
    """Fuses dense and sparse retrieval via Reciprocal Rank Fusion."""

    name = "hybrid"

    def __init__(self, dense: Retriever, sparse: Retriever, *, rrf_k: int = 60) -> None:
        self._dense = dense
        self._sparse = sparse
        self._rrf_k = rrf_k

    @classmethod
    def from_settings(cls, settings: Settings) -> HybridRetriever:
        return cls(
            DenseRetriever.from_settings(settings),
            SparseRetriever.from_settings(settings),
            rrf_k=settings.RRF_K,
        )

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        # Over-fetch from each arm so fusion has depth to work with.
        fetch_k = max(top_k * 2, 20)
        dense = await self._dense.retrieve(
            query, namespace=namespace, top_k=fetch_k, document_ids=document_ids
        )
        sparse = await self._sparse.retrieve(
            query, namespace=namespace, top_k=fetch_k, document_ids=document_ids
        )

        fused: dict[str, float] = {}
        chunks: dict[str, RetrievedChunk] = {}
        for ranking in (dense, sparse):
            for rank, item in enumerate(ranking):
                cid = item.chunk.id
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (self._rrf_k + rank + 1)
                chunks.setdefault(cid, item)

        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
        results: list[RetrievedChunk] = []
        for cid, score in ordered[:top_k]:
            base = chunks[cid]
            results.append(RetrievedChunk(chunk=base.chunk, score=score, source="hybrid"))
        return results
