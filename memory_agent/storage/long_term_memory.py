"""Long-term memory: durable per-user facts with semantic recall.

Facts are stored as short natural-language statements ("User is a vegetarian",
"User's dog is named Rex"). Each is embedded with an OpenAI embedding model so
we can recall the most relevant ones for a given query via cosine similarity.

Recall is a single vectorised matrix operation over the user's stored vectors —
fast for the thousands-of-facts scale a personal assistant reaches. Swap in a
vector DB here if you ever need more.
"""

from __future__ import annotations

import numpy as np

from .database import Database


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
            blob = _to_blob(self.embeddings.embed_query(content))
        except Exception:
            # If embedding fails (e.g. offline) we still keep the fact; it just
            # won't participate in semantic search until re-embedded.
            blob = None
        self.db.insert_memory(user_id, content, blob)

    def search(self, user_id: str, query: str) -> list[str]:
        """Return the most relevant stored facts for ``query``."""
        rows = self.db.all_memories(user_id)
        if not rows:
            # Fast path: no embedding call for users with nothing stored.
            return []

        embedded = [r for r in rows if r["embedding"] is not None]
        if not embedded:
            # No vectors available: fall back to the most recent facts.
            return [r["content"] for r in rows[-self.top_k :]]

        try:
            q = np.asarray(self.embeddings.embed_query(query), dtype=np.float32)
        except Exception:
            return [r["content"] for r in embedded[-self.top_k :]]

        # Stack vectors into one matrix and score them all at once.
        matrix = np.vstack([_from_blob(r["embedding"]) for r in embedded])
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0] = 1.0
        q_norm = np.linalg.norm(q) or 1.0
        scores = (matrix @ q) / (norms * q_norm)

        order = np.argsort(scores)[::-1][: self.top_k]
        return [embedded[i]["content"] for i in order if scores[i] >= self.min_score]

    def list_all(self, user_id: str) -> list[str]:
        return [r["content"] for r in self.db.all_memories(user_id)]
