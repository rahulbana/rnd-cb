"""VectorStore port -- persists and searches embedded chunks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.domain.models import Chunk, EmbeddingVector, RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class VectorStore(Protocol):
    """Any vector database must satisfy this.

    ``namespace`` scopes every operation to an org/collection -- the hook that
    turns single-tenant into multi-tenant later without a schema change.
    """

    name: str  # "chroma" | "pgvector" | "pinecone" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> VectorStore:
        """Construct the adapter from application settings."""
        ...

    async def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[EmbeddingVector],
        *,
        namespace: str,
    ) -> None:
        """Insert or replace chunk vectors within a namespace."""
        ...

    async def search(
        self,
        query: EmbeddingVector,
        *,
        namespace: str,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        """Return the ``top_k`` most similar chunks in a namespace."""
        ...

    async def delete(self, chunk_ids: Sequence[str], *, namespace: str) -> None:
        """Remove chunks by id from a namespace."""
        ...
