"""Memory subsystem.

Short-term memory
    The most recent N messages of the *current* session, passed back to the
    model so it remembers the ongoing conversation.

Long-term memory
    Durable facts about the user, extracted from conversations and stored in
    the `memories` table with an embedding vector. On each new request the
    most semantically-relevant memories (across all of the user's sessions)
    are retrieved and injected into the system prompt.
"""

from __future__ import annotations

import json
import logging

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .llm import chat_completion, embed
from .models import Memory, Message

logger = logging.getLogger(__name__)


# ---- Short-term memory ----
def get_short_term_messages(db: Session, session_id: int) -> list[dict]:
    """Return the recent conversation turns as OpenAI chat messages."""
    # Order by id (monotonic insertion order) so rows with identical
    # created_at timestamps still window/sort deterministically.
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .limit(settings.short_term_window)
    )
    rows = list(db.scalars(stmt))
    rows.reverse()  # chronological order
    return [{"role": m.role, "content": m.content} for m in rows]


# ---- Long-term memory ----
def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def retrieve_long_term(
    db: Session, user_id: int, query: str, *, trace=None
) -> list[str]:
    """Return the top-K long-term memories most relevant to `query`."""
    memories = list(
        db.scalars(select(Memory).where(Memory.user_id == user_id))
    )
    if not memories:
        return []

    top_k = settings.long_term_top_k
    query_vec = embed(query, trace=trace)

    if query_vec is None:
        # Fallback: no embeddings available -> return most recent memories.
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return [m.content for m in memories[:top_k]]

    q = np.array(query_vec, dtype=np.float32)
    scored: list[tuple[float, Memory]] = []
    for mem in memories:
        if not mem.embedding:
            continue
        try:
            vec = np.array(json.loads(mem.embedding), dtype=np.float32)
        except (ValueError, TypeError):
            continue
        scored.append((_cosine(q, vec), mem))

    if not scored:
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return [m.content for m in memories[:top_k]]

    scored.sort(key=lambda t: t[0], reverse=True)
    return [mem.content for _, mem in scored[:top_k]]


_EXTRACTION_PROMPT = (
    "You maintain a long-term memory about a user for a chatbot. "
    "From the latest exchange below, extract durable facts, preferences, or "
    "personal details worth remembering across future conversations "
    "(e.g. name, location, job, goals, likes/dislikes). "
    "Return a JSON object: {\"memories\": [\"fact 1\", \"fact 2\"]}. "
    "Only include genuinely durable facts. If there is nothing worth "
    "remembering, return {\"memories\": []}."
)


def extract_and_store_memories(
    db: Session,
    user_id: int,
    user_message: str,
    assistant_message: str,
    *,
    trace=None,
) -> list[str]:
    """Extract durable facts from an exchange and persist them as memories."""
    exchange = f"User: {user_message}\nAssistant: {assistant_message}"
    try:
        raw = chat_completion(
            [
                {"role": "system", "content": _EXTRACTION_PROMPT},
                {"role": "user", "content": exchange},
            ],
            trace=trace,
            generation_name="memory-extraction",
        )
        data = json.loads(_strip_json(raw))
        facts = data.get("memories", []) if isinstance(data, dict) else []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Memory extraction failed: %s", exc)
        return []

    stored: list[str] = []
    for fact in facts:
        if not isinstance(fact, str) or not fact.strip():
            continue
        fact = fact.strip()
        if _is_duplicate(db, user_id, fact):
            continue
        vec = embed(fact, trace=trace)
        db.add(
            Memory(
                user_id=user_id,
                content=fact,
                embedding=json.dumps(vec) if vec is not None else None,
            )
        )
        stored.append(fact)

    if stored:
        db.commit()
    return stored


def _is_duplicate(db: Session, user_id: int, fact: str) -> bool:
    existing = db.scalars(
        select(Memory.content).where(Memory.user_id == user_id)
    ).all()
    fact_l = fact.lower()
    return any(fact_l == e.lower() for e in existing)


def _strip_json(text: str) -> str:
    """Strip markdown code fences the model may wrap JSON in."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return text.strip()
