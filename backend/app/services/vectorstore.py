"""ChromaDB-backed vector store for semantic search, RAG and dedup.

Falls back to a lightweight in-memory cosine index if ``chromadb`` is
not installed, so the API keeps working in minimal environments.
"""
from __future__ import annotations

import logging
import threading

from app.core.config import settings
from app.services.embeddings import get_embedder

logger = logging.getLogger(__name__)


def _doc_text(title: str, body: str, summary: str) -> str:
    return f"{title}\n\n{summary}\n\n{body}".strip()


class _InMemoryIndex:
    """Minimal cosine-similarity fallback (no persistence)."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _cosine_distance(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return 1.0 - dot  # vectors are pre-normalised

    def upsert(self, id: str, embedding: list[float], metadata: dict) -> None:
        with self._lock:
            self._data[id] = {"embedding": embedding, "metadata": metadata}

    def delete(self, id: str) -> None:
        with self._lock:
            self._data.pop(id, None)

    def query(self, embedding: list[float], user_id: str, n: int):
        with self._lock:
            scored = [
                (rid, self._cosine_distance(embedding, rec["embedding"]), rec["metadata"])
                for rid, rec in self._data.items()
                if rec["metadata"].get("user_id") == user_id
            ]
        scored.sort(key=lambda x: x[1])
        return scored[:n]


class VectorStore:
    def __init__(self) -> None:
        self._embedder = get_embedder()
        self._backend = "memory"
        self._collection = None
        self._memory = _InMemoryIndex()
        self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb

            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self._collection = client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._backend = "chroma"
            logger.info("VectorStore using ChromaDB at %s", settings.CHROMA_PERSIST_DIR)
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "ChromaDB unavailable (%s); using in-memory vector index.", exc
            )

    # --- write ------------------------------------------------------
    def upsert_article(
        self, *, article_id: str, user_id: str, title: str, body: str, summary: str
    ) -> None:
        text = _doc_text(title, body, summary)
        embedding = self._embedder.embed_one(text)
        metadata = {"user_id": user_id, "title": title or "Untitled"}
        if self._backend == "chroma":
            self._collection.upsert(
                ids=[article_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text[:2000]],
            )
        else:
            self._memory.upsert(article_id, embedding, metadata)

    def delete_article(self, article_id: str) -> None:
        if self._backend == "chroma":
            try:
                self._collection.delete(ids=[article_id])
            except Exception:  # pragma: no cover
                pass
        else:
            self._memory.delete(article_id)

    # --- read -------------------------------------------------------
    def search(
        self, *, query: str, user_id: str, n_results: int = 10
    ) -> list[tuple[str, float]]:
        """Return (article_id, distance) pairs, closest first."""
        embedding = self._embedder.embed_one(query)
        return self._query(embedding, user_id, n_results)

    def find_similar(
        self, *, title: str, body: str, summary: str, user_id: str, n_results: int = 5
    ) -> list[tuple[str, float]]:
        embedding = self._embedder.embed_one(_doc_text(title, body, summary))
        return self._query(embedding, user_id, n_results)

    def _query(
        self, embedding: list[float], user_id: str, n: int
    ) -> list[tuple[str, float]]:
        if self._backend == "chroma":
            res = self._collection.query(
                query_embeddings=[embedding],
                n_results=n,
                where={"user_id": user_id},
            )
            ids = res.get("ids", [[]])[0]
            dists = res.get("distances", [[]])[0]
            return list(zip(ids, dists))
        return [(rid, dist) for rid, dist, _ in self._memory.query(embedding, user_id, n)]


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
