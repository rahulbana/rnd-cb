"""ChromaDB-backed vector store (persistent, local).

Embeddings are computed by our own embedder and passed in explicitly, so the
store stays a pure index — swapping ChromaDB for another backend later means
implementing the same ``BaseVectorStore`` interface, nothing else changes.
"""
from __future__ import annotations

from typing import Any

from .base import BaseVectorStore, SearchResult, VectorRecord
from ..config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)


def _flatten_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Chroma only accepts scalar metadata values; serialize lists/dicts."""
    out: dict[str, Any] = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = ",".join(str(x) for x in v) if isinstance(v, (list, tuple)) else str(v)
    return out


class ChromaVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        import chromadb

        settings = get_settings()
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        # Cosine space matches our normalized embeddings.
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name, metadata={"hnsw:space": "cosine"}
        )

    def add(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._collection.add(
            ids=[r.id for r in records],
            documents=[r.text for r in records],
            embeddings=[r.embedding for r in records],
            metadatas=[_flatten_metadata(r.metadata) for r in records],
        )

    def query(self, embedding: list[float], top_k: int,
              where: dict | None = None) -> list[SearchResult]:
        res = self._collection.query(
            query_embeddings=[embedding], n_results=top_k, where=where,
            include=["documents", "metadatas", "distances"],
        )
        results: list[SearchResult] = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for _id, doc, meta, dist in zip(ids, docs, metas, dists):
            # cosine distance -> similarity
            results.append(SearchResult(id=_id, text=doc, metadata=meta or {},
                                        score=1.0 - float(dist)))
        return results

    def all_documents(self) -> list[SearchResult]:
        res = self._collection.get(include=["documents", "metadatas"])
        out: list[SearchResult] = []
        for _id, doc, meta in zip(res.get("ids", []), res.get("documents", []),
                                  res.get("metadatas", [])):
            out.append(SearchResult(id=_id, text=doc, metadata=meta or {}, score=0.0))
        return out

    def count(self) -> int:
        return self._collection.count()

    def list_sources(self) -> list[dict]:
        res = self._collection.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for meta in res.get("metadatas", []):
            src = (meta or {}).get("source", "unknown")
            counts[src] = counts.get(src, 0) + 1
        return [{"source": s, "chunks": c} for s, c in sorted(counts.items())]

    def delete_source(self, source: str) -> None:
        self._collection.delete(where={"source": source})
