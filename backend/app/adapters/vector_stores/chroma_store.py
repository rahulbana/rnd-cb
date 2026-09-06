"""Chroma vector store adapter (default).

Supports an HTTP server (compose/prod) and embedded ephemeral/persistent
clients (dev/tests). The client is built lazily so constructing the adapter --
as the registry does at startup -- never imports chromadb or opens a
connection. Each org maps to its own collection (the multi-tenancy hook).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.domain.models import Chunk, ChunkMetadata, EmbeddingVector, RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings

_NAME_SANITIZE = re.compile(r"[^a-zA-Z0-9._-]")


def _collection_name(namespace: str) -> str:
    """Map an org namespace to a valid Chroma collection name (3-512 chars)."""
    safe = _NAME_SANITIZE.sub("_", namespace)
    name = f"ns_{safe}"
    if not name[-1].isalnum():
        name = f"{name}0"
    return name[:512]


class ChromaVectorStore:
    """Persists and searches chunk vectors in Chroma."""

    name = "chroma"

    def __init__(
        self,
        *,
        client: Any | None = None,
        mode: str = "http",
        host: str = "localhost",
        port: int = 8000,
        persist_dir: str = "./data/chroma",
        space: str = "cosine",
    ) -> None:
        self._client = client
        self._mode = mode
        self._host = host
        self._port = port
        self._persist_dir = persist_dir
        self._space = space

    @classmethod
    def from_settings(cls, settings: Settings) -> ChromaVectorStore:
        return cls(
            mode=settings.CHROMA_MODE,
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            persist_dir=settings.CHROMA_PERSIST_DIR,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            import chromadb  # lazy import

            if self._mode == "ephemeral":
                self._client = chromadb.EphemeralClient()
            elif self._mode == "persistent":
                self._client = chromadb.PersistentClient(path=self._persist_dir)
            else:
                self._client = chromadb.HttpClient(host=self._host, port=self._port)
        return self._client

    def _collection(self, namespace: str) -> Any:
        return self._get_client().get_or_create_collection(
            name=_collection_name(namespace),
            metadata={"hnsw:space": self._space},
        )

    async def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[EmbeddingVector],
        *,
        namespace: str,
    ) -> None:
        if not chunks:
            return
        collection = self._collection(namespace)
        collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=[v.values for v in vectors],
            documents=[c.text for c in chunks],
            metadatas=[self._metadata(c) for c in chunks],
        )

    async def search(
        self,
        query: EmbeddingVector,
        *,
        namespace: str,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        collection = self._collection(namespace)
        result = collection.query(
            query_embeddings=[query.values],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        retrieved: list[RetrievedChunk] = []
        for cid, text, meta, distance in zip(
            ids, documents, metadatas, distances, strict=False
        ):
            retrieved.append(
                RetrievedChunk(
                    chunk=self._to_chunk(cid, text, meta or {}),
                    score=1.0 - float(distance),  # cosine distance -> similarity
                    source="dense",
                )
            )
        return retrieved

    async def delete(self, chunk_ids: Sequence[str], *, namespace: str) -> None:
        if not chunk_ids:
            return
        self._collection(namespace).delete(ids=list(chunk_ids))

    @staticmethod
    def _metadata(chunk: Chunk) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "document_id": chunk.metadata.document_id,
            "ordinal": chunk.metadata.ordinal,
        }
        if chunk.metadata.page is not None:
            meta["page"] = chunk.metadata.page
        if chunk.metadata.heading_path is not None:
            meta["heading_path"] = chunk.metadata.heading_path
        return meta

    @staticmethod
    def _to_chunk(cid: str, text: str, meta: dict[str, Any]) -> Chunk:
        return Chunk(
            id=cid,
            text=text or "",
            metadata=ChunkMetadata(
                document_id=str(meta.get("document_id", "")),
                page=meta.get("page"),
                heading_path=meta.get("heading_path"),
                ordinal=int(meta.get("ordinal", 0)),
            ),
        )
