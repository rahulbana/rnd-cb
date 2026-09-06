"""Postgres + pgvector vector store adapter.

Keeps vectors in the same database as the relational metadata. Requires the
``vector`` extension; the engine, extension, and table are set up lazily on
first use so constructing the adapter never touches the database. Cosine
distance drives similarity, matching the Chroma adapter's semantics so a
provider swap is behaviourally consistent.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import Chunk, ChunkMetadata, EmbeddingVector, RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings


class PgVectorStore:
    """Persists and searches chunk vectors in Postgres via pgvector."""

    name = "pgvector"

    def __init__(
        self, database_url: str, dim: int, table_name: str = "vector_chunks"
    ) -> None:
        self._url = database_url
        self._dim = dim
        self._table_name = table_name
        self._engine: Any | None = None
        self._table: Any | None = None
        self._ready = False

    @classmethod
    def from_settings(cls, settings: Settings) -> PgVectorStore:
        return cls(database_url=settings.DATABASE_URL, dim=settings.EMBED_DIM)

    def _ensure_ready(self) -> tuple[Any, Any]:
        if self._ready:
            return self._engine, self._table

        from pgvector.sqlalchemy import Vector  # lazy import
        from sqlalchemy import (
            Column,
            Integer,
            MetaData,
            String,
            Table,
            Text,
            create_engine,
            text,
        )

        engine = create_engine(self._url, pool_pre_ping=True, future=True)
        metadata = MetaData()
        table = Table(
            self._table_name,
            metadata,
            Column("id", String(128), primary_key=True),
            Column("namespace", String(64), index=True, nullable=False),
            Column("document_id", String(36), index=True, nullable=False),
            Column("page", Integer, nullable=True),
            Column("heading_path", String(1024), nullable=True),
            Column("ordinal", Integer, nullable=False, default=0),
            Column("text", Text, nullable=False),
            Column("embedding", Vector(self._dim), nullable=False),
        )
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            metadata.create_all(conn)

        self._engine, self._table, self._ready = engine, table, True
        return engine, table

    async def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[EmbeddingVector],
        *,
        namespace: str,
    ) -> None:
        if not chunks:
            return

        def _run() -> None:
            from sqlalchemy.dialects.postgresql import insert

            engine, table = self._ensure_ready()
            rows = [
                {
                    "id": chunk.id,
                    "namespace": namespace,
                    "document_id": chunk.metadata.document_id,
                    "page": chunk.metadata.page,
                    "heading_path": chunk.metadata.heading_path,
                    "ordinal": chunk.metadata.ordinal,
                    "text": chunk.text,
                    "embedding": vector.values,
                }
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            stmt = insert(table).values(rows)
            update = {
                c: stmt.excluded[c]
                for c in (
                    "namespace",
                    "document_id",
                    "page",
                    "heading_path",
                    "ordinal",
                    "text",
                    "embedding",
                )
            }
            stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update)
            with engine.begin() as conn:
                conn.execute(stmt)

        await asyncio.to_thread(_run)

    async def search(
        self,
        query: EmbeddingVector,
        *,
        namespace: str,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        def _run() -> list[RetrievedChunk]:
            from sqlalchemy import select

            engine, table = self._ensure_ready()
            distance = table.c.embedding.cosine_distance(query.values)
            stmt = (
                select(
                    table.c.id,
                    table.c.document_id,
                    table.c.page,
                    table.c.heading_path,
                    table.c.ordinal,
                    table.c.text,
                    distance.label("distance"),
                )
                .where(table.c.namespace == namespace)
                .order_by(distance)
                .limit(top_k)
            )
            with engine.connect() as conn:
                results = conn.execute(stmt).all()

            return [
                RetrievedChunk(
                    chunk=Chunk(
                        id=row.id,
                        text=row.text,
                        metadata=ChunkMetadata(
                            document_id=row.document_id,
                            page=row.page,
                            heading_path=row.heading_path,
                            ordinal=row.ordinal,
                        ),
                    ),
                    score=1.0 - float(row.distance),
                    source="dense",
                )
                for row in results
            ]

        return await asyncio.to_thread(_run)

    async def delete(self, chunk_ids: Sequence[str], *, namespace: str) -> None:
        if not chunk_ids:
            return

        def _run() -> None:
            from sqlalchemy import delete

            engine, table = self._ensure_ready()
            stmt = delete(table).where(
                table.c.namespace == namespace, table.c.id.in_(list(chunk_ids))
            )
            with engine.begin() as conn:
                conn.execute(stmt)

        await asyncio.to_thread(_run)
