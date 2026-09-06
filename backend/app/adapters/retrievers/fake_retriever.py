"""In-memory fake retriever -- embeds the query and searches the fake store.

Wires the embedder and vector-store ports together to return candidates.
Later phases replace this with dense/sparse/hybrid strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.domain.interfaces import Embedder, VectorStore


class FakeRetriever:
    """Dense-only retriever over the injected embedder + vector store."""

    name = "fake"

    def __init__(self, embedder: Embedder, vector_store: VectorStore) -> None:
        self._embedder = embedder
        self._vector_store = vector_store

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeRetriever:
        # Import here to avoid a circular import with the registry.
        from app.core.registry import get_embedder, get_vector_store

        return cls(get_embedder(), get_vector_store())

    async def retrieve(
        self, query: str, *, namespace: str, top_k: int = 10
    ) -> list[RetrievedChunk]:
        vector = await self._embedder.embed_query(query)
        return await self._vector_store.search(vector, namespace=namespace, top_k=top_k)
