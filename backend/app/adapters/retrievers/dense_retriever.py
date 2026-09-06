"""Dense retriever -- embed the query and search the vector store."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.domain.interfaces import Embedder, VectorStore


class DenseRetriever:
    """Semantic retrieval over the injected embedder + vector store."""

    name = "dense"

    def __init__(self, embedder: Embedder, vector_store: VectorStore) -> None:
        self._embedder = embedder
        self._vector_store = vector_store

    @classmethod
    def from_settings(cls, settings: Settings) -> DenseRetriever:
        from app.core.registry import get_embedder, get_vector_store

        return cls(get_embedder(), get_vector_store())

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        vector = await self._embedder.embed_query(query)
        # Over-fetch when scoping so the post-filter still returns ~top_k.
        fetch_k = top_k * 4 if document_ids else top_k
        results = await self._vector_store.search(
            vector, namespace=namespace, top_k=fetch_k
        )
        if document_ids is not None:
            allowed = set(document_ids)
            results = [r for r in results if r.chunk.metadata.document_id in allowed]
        for r in results:
            r.source = "dense"
        return results[:top_k]
