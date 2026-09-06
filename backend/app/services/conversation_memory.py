"""Conversation memory: sliding window + summarization, persisted per turn.

Recent turns are kept verbatim (a sliding window); older turns are optionally
summarized into a single synthetic system message so long conversations stay
within the context budget. Every turn is persisted with its citations,
provider, token counts, and latency -- the full cost/latency trail.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message
from app.domain.models import ChatMessage, Citation, Role

if TYPE_CHECKING:
    from app.domain.interfaces import LLMProvider

# Strictly-monotonic timestamps so message ordering is deterministic even when
# several turns are written within the same clock tick (SQLite second-res, or a
# Postgres transaction whose now() is constant).
_ts_lock = threading.Lock()
_last_ts: datetime | None = None


def _mono_now() -> datetime:
    global _last_ts
    with _ts_lock:
        now = datetime.now(UTC)
        if _last_ts is not None and now <= _last_ts:
            now = _last_ts + timedelta(microseconds=1)
        _last_ts = now
        return now


_SUMMARY_SYSTEM = (
    "Summarize the following conversation so far in 3-4 sentences, preserving "
    "facts and any decisions. Reply with only the summary."
)


class ConversationMemory:
    """Loads, summarizes, and persists conversation turns."""

    def __init__(
        self,
        db: Session,
        llm: LLMProvider,
        *,
        window: int = 6,
        summarize: bool = True,
    ) -> None:
        self._db = db
        self._llm = llm
        self._window = window
        self._summarize = summarize

    def ensure_conversation(
        self, conversation_id: str | None, *, user_id: str, title: str
    ) -> Conversation:
        if conversation_id is not None:
            conv = self._db.get(Conversation, conversation_id)
            if conv is not None:
                return conv
        conv = Conversation(user_id=user_id, title=title[:120] or "New conversation")
        self._db.add(conv)
        self._db.commit()
        self._db.refresh(conv)
        return conv

    def _messages(self, conversation_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(self._db.execute(stmt).scalars().all())

    async def history(self, conversation_id: str) -> list[ChatMessage]:
        """Return prior turns as chat messages, summarizing overflow."""
        rows = self._messages(conversation_id)
        recent = rows[-self._window :]
        older = rows[: -self._window] if len(rows) > self._window else []

        history: list[ChatMessage] = []
        if older and self._summarize:
            summary = await self._summarize_rows(older)
            if summary:
                history.append(
                    ChatMessage(
                        role=Role.SYSTEM,
                        content=f"Summary of earlier conversation: {summary}",
                    )
                )
        for row in recent:
            history.append(ChatMessage(role=Role(row.role), content=row.content))
        return history

    async def _summarize_rows(self, rows: list[Message]) -> str:
        transcript = "\n".join(f"{r.role}: {r.content}" for r in rows)
        resp = await self._llm.generate(
            [
                ChatMessage(role=Role.SYSTEM, content=_SUMMARY_SYSTEM),
                ChatMessage(role=Role.USER, content=transcript),
            ],
            temperature=0.0,
        )
        return resp.content.strip()

    def persist(
        self,
        conversation_id: str,
        *,
        role: Role,
        content: str,
        citations: list[Citation] | None = None,
        provider: str | None = None,
        prompt_version: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role.value,
            content=content,
            created_at=_mono_now(),
            citations=([c.model_dump() for c in citations] if citations else None),
            provider=provider,
            prompt_version=prompt_version,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
        )
        self._db.add(message)
        self._db.commit()
        self._db.refresh(message)
        return message

    @staticmethod
    def serialize_citations(raw: object) -> list[dict]:
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return []
        return []
