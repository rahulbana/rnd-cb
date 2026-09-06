"""Ingestion orchestration -- chunker -> embedder -> vector store.

Depends only on ports resolved through the registry. Turns a ``ParsedDocument``
into embedded, indexed, retrievable chunks within an org namespace. Phase 4
moves this off the request thread; the wiring shape is set here.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.domain.interfaces import Chunker, Embedder, VectorStore
from app.domain.models import Chunk, ParsedDocument, RetrievedChunk

logger = get_logger("service.ingestion")


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
        self, parsed: ParsedDocument, *, document_id: str, namespace: str
    ) -> list[Chunk]:
        """Chunk, embed, and upsert a parsed document; return the chunks."""
        if self._chunker is None:
            raise RuntimeError("IngestionService.index requires a chunker")
        chunks = self._chunker.chunk(parsed, document_id=document_id)
        if not chunks:
            logger.info("index_no_chunks", document_id=document_id)
            return []
        vectors = await self._embedder.embed_documents([c.text for c in chunks])
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
