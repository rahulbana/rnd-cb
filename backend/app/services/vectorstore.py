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
        self._collection = None  # articles
        self._style_collection = None  # style references
        self._memory = _InMemoryIndex()  # articles
        self._style_memory = _InMemoryIndex()  # style references
        self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._style_collection = client.get_or_create_collection(
                name=f"{settings.CHROMA_COLLECTION}_style",
                metadata={"hnsw:space": "cosine"},
            )
            self._backend = "chroma"
            logger.info("VectorStore using ChromaDB at %s", settings.CHROMA_PERSIST_DIR)
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "ChromaDB unavailable (%s); using in-memory vector index.", exc
            )

    # --- generic helpers -------------------------------------------
    def _upsert(self, collection, memory, doc_id, embedding, metadata, document):
        if self._backend == "chroma":
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document[:2000]],
            )
        else:
            memory.upsert(doc_id, embedding, metadata)

    def _delete(self, collection, memory, doc_id):
        if self._backend == "chroma":
            try:
                collection.delete(ids=[doc_id])
            except Exception:  # pragma: no cover
                pass
        else:
            memory.delete(doc_id)

    def _query_index(self, collection, memory, embedding, user_id, n):
        if self._backend == "chroma":
            res = collection.query(
                query_embeddings=[embedding],
                n_results=n,
                where={"user_id": user_id},
            )
            ids = res.get("ids", [[]])[0]
            dists = res.get("distances", [[]])[0]
            return list(zip(ids, dists))
        return [(rid, dist) for rid, dist, _ in memory.query(embedding, user_id, n)]

    # --- articles ---------------------------------------------------
    def upsert_article(
        self, *, article_id: str, user_id: str, title: str, body: str, summary: str
    ) -> None:
        text = _doc_text(title, body, summary)
        embedding = self._embedder.embed_one(text)
        metadata = {"user_id": user_id, "title": title or "Untitled"}
        self._upsert(self._collection, self._memory, article_id, embedding, metadata, text)

    def delete_article(self, article_id: str) -> None:
        self._delete(self._collection, self._memory, article_id)

    def search(
        self, *, query: str, user_id: str, n_results: int = 10
    ) -> list[tuple[str, float]]:
        """Return (article_id, distance) pairs, closest first."""
        embedding = self._embedder.embed_one(query)
        return self._query_index(self._collection, self._memory, embedding, user_id, n_results)

    def find_similar(
        self, *, title: str, body: str, summary: str, user_id: str, n_results: int = 5
    ) -> list[tuple[str, float]]:
        embedding = self._embedder.embed_one(_doc_text(title, body, summary))
        return self._query_index(self._collection, self._memory, embedding, user_id, n_results)

    # --- style references ------------------------------------------
    def upsert_style_reference(
        self, *, ref_id: str, user_id: str, name: str, content: str
    ) -> None:
        text = f"{name}\n\n{content}".strip()
        embedding = self._embedder.embed_one(text)
        metadata = {"user_id": user_id, "title": name or "Untitled"}
        self._upsert(
            self._style_collection, self._style_memory, ref_id, embedding, metadata, text
        )

    def delete_style_reference(self, ref_id: str) -> None:
        self._delete(self._style_collection, self._style_memory, ref_id)

    def search_style_references(
        self, *, query: str, user_id: str, n_results: int = 3
    ) -> list[tuple[str, float]]:
        embedding = self._embedder.embed_one(query)
        return self._query_index(
            self._style_collection, self._style_memory, embedding, user_id, n_results
        )


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
