"""Long-term memory: durable per-user facts with semantic recall.

Facts are stored as short natural-language statements ("User is a vegetarian",
"User's dog is named Rex"). Each is embedded with an OpenAI embedding model so
we can recall the most relevant ones for a given query via cosine similarity.

This is deliberately simple (an in-process cosine scan) which is plenty fast for
a personal CLI assistant. Swap in a vector DB here if you ever need scale.
"""

from __future__ import annotations

import numpy as np

from .db import Database


def _to_blob(vec: list[float]) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def _from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


class LongTermMemory:
    """Store and retrieve durable facts about a user."""

    def __init__(self, db: Database, embeddings, top_k: int = 5, min_score: float = 0.25):
        self.db = db
        self.embeddings = embeddings
        self.top_k = top_k
        self.min_score = min_score

    def add(self, user_id: str, content: str) -> None:
        """Persist a durable fact, embedding it for later semantic recall."""
        content = content.strip()
        if not content:
            return
        try:
            vec = self.embeddings.embed_query(content)
            blob = _to_blob(vec)
        except Exception:
            # If embedding fails (e.g. offline) we still keep the fact; it just
            # won't participate in semantic search until re-embedded.
            blob = None
        self.db.insert_memory(user_id, content, blob)

    def search(self, user_id: str, query: str) -> list[str]:
        """Return the most relevant stored facts for ``query``."""
        rows = self.db.all_memories(user_id)
        if not rows:
            return []

        embedded = [r for r in rows if r["embedding"] is not None]
        if not embedded:
            # No vectors available: fall back to the most recent facts.
            return [r["content"] for r in rows[-self.top_k :]]

        try:
            q = np.asarray(self.embeddings.embed_query(query), dtype=np.float32)
        except Exception:
            return [r["content"] for r in embedded[-self.top_k :]]

        q_norm = np.linalg.norm(q) or 1.0
        scored: list[tuple[float, str]] = []
        for r in embedded:
            v = _from_blob(r["embedding"])
            denom = (np.linalg.norm(v) or 1.0) * q_norm
            score = float(np.dot(v, q) / denom)
            scored.append((score, r["content"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for s, c in scored[: self.top_k] if s >= self.min_score]

    def list_all(self, user_id: str) -> list[str]:
        return [r["content"] for r in self.db.all_memories(user_id)]
