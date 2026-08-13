"""Optional long-term vector memory backed by ChromaDB + sentence-transformers.

Entirely optional. If ``AUTODEV_MEMORY_ENABLED`` is false or the heavy
dependencies aren't installed, every method degrades to a safe no-op so the
rest of the app keeps working. When enabled, the agent stores summaries of
what it built and can recall relevant context on later, related projects.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..config import get_settings

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = self.settings.memory_enabled
        self._client = None
        self._embedder = None
        self._collection = None
        if self.enabled:
            self._try_init()

    def _try_init(self) -> None:
        try:
            import chromadb  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._client = chromadb.PersistentClient(
                path=str(self.settings.memory_dir_path)
            )
            self._collection = self._client.get_or_create_collection("autodev")
            self._embedder = SentenceTransformer(self.settings.embedding_model)
            logger.info("Long-term memory enabled (chromadb + %s)",
                        self.settings.embedding_model)
        except Exception as exc:  # pragma: no cover - optional path
            logger.warning(
                "Memory requested but unavailable (%s). Install "
                "requirements-memory.txt. Continuing without memory.",
                exc,
            )
            self.enabled = False

    def _embed(self, texts: list[str]) -> list[list[float]]:
        assert self._embedder is not None
        return [v.tolist() for v in self._embedder.encode(texts)]

    def add(self, project_id: str, doc_id: str, text: str,
            metadata: Optional[dict] = None) -> None:
        if not self.enabled or self._collection is None:
            return
        try:
            self._collection.upsert(
                ids=[f"{project_id}:{doc_id}"],
                embeddings=self._embed([text]),
                documents=[text],
                metadatas=[{"project_id": project_id, **(metadata or {})}],
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("memory.add failed: %s", exc)

    def query(self, text: str, k: int = 4) -> list[str]:
        if not self.enabled or self._collection is None:
            return []
        try:
            res = self._collection.query(
                query_embeddings=self._embed([text]), n_results=k
            )
            docs = res.get("documents") or [[]]
            return docs[0]
        except Exception as exc:  # pragma: no cover
            logger.warning("memory.query failed: %s", exc)
            return []


_store: Optional[MemoryStore] = None


def get_memory() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
