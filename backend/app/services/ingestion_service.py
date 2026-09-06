"""Ingestion orchestration -- parser -> chunker -> embedder -> vector store.

Depends only on ports resolved through the registry. Phase 2-4 flesh out the
stages; the wiring shape is set here.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.domain.interfaces import Chunker, Embedder, Parser, VectorStore

logger = get_logger("service.ingestion")


class IngestionService:
    """Coordinates the ingestion pipeline over injected ports."""

    def __init__(
        self,
        parser: Parser,
        chunker: Chunker,
        embedder: Embedder,
        vector_store: VectorStore,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store

    async def ingest(
        self,
        data: bytes,
        *,
        filename: str,
        mime_type: str,
        document_id: str,
        namespace: str,
    ) -> int:
        """Run the full pipeline; returns the number of chunks indexed."""
        parsed = await self._parser.parse(data, filename=filename, mime_type=mime_type)
        chunks = self._chunker.chunk(parsed, document_id=document_id)
        vectors = await self._embedder.embed_documents([c.text for c in chunks])
        await self._vector_store.upsert(chunks, vectors, namespace=namespace)
        logger.info(
            "ingested",
            document_id=document_id,
            chunks=len(chunks),
            parser=parsed.parser_name,
        )
        return len(chunks)
