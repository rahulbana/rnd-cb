"""Ingestion orchestration -- chunker -> embedder -> vector store.

Depends only on ports resolved through the registry. Turns a ``ParsedDocument``
into embedded, indexed, retrievable chunks within an org namespace. The
optional ``on_stage`` callback lets a caller (the async job runner) report
per-stage progress mid-flight.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.domain.models import Chunk, ParsedDocument, RetrievedChunk

if TYPE_CHECKING:
    from app.domain.interfaces import Chunker, Embedder, VectorStore

logger = get_logger("service.ingestion")

# stage name -> percent-complete checkpoint
StageCallback = Callable[[str, int], None]


def _noop_stage(stage: str, percent: int) -> None:
    return None


class IngestionService:
    """Coordinates chunking, embedding, and indexing over injected ports."""

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        chunker: Chunker | None = None,
    ) -> None:
        # chunker is optional: the search path only needs embedder + store.
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store

    async def index(
        self,
        parsed: ParsedDocument,
        *,
        document_id: str,
        namespace: str,
        on_stage: StageCallback = _noop_stage,
    ) -> list[Chunk]:
        """Chunk, embed, and upsert a parsed document; return the chunks."""
        if self._chunker is None:
            raise RuntimeError("IngestionService.index requires a chunker")

        on_stage("chunking", 40)
        chunks = self._chunker.chunk(parsed, document_id=document_id)
        if not chunks:
            logger.info("index_no_chunks", document_id=document_id)
            return []

        on_stage("embedding", 60)
        vectors = await self._embedder.embed_documents([c.text for c in chunks])

        on_stage("indexing", 85)
        await self._vector_store.upsert(chunks, vectors, namespace=namespace)

        logger.info(
            "indexed",
            document_id=document_id,
            namespace=namespace,
            chunks=len(chunks),
            chunker=self._chunker.name,
            embedder=self._embedder.name,
            vector_store=self._vector_store.name,
            embed_dim=vectors[0].dim,
        )
        return chunks

    async def search(
        self, query: str, *, namespace: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        """Raw dense similarity search: embed the query and query the store."""
        vector = await self._embedder.embed_query(query)
        return await self._vector_store.search(vector, namespace=namespace, top_k=top_k)

    async def remove(self, vector_ids: list[str], *, namespace: str) -> None:
        """Delete vectors from the store (used for idempotent re-indexing)."""
        if vector_ids:
            await self._vector_store.delete(vector_ids, namespace=namespace)
