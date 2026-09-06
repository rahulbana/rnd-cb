"""Analytics queries: usage, cost, latency, top documents, feedback, queue.

All scoped to an org (messages -> conversations -> users -> org). Feeds the
admin/analytics dashboard.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Conversation,
    Document,
    Feedback,
    IngestionJob,
    Message,
    User,
)
from app.services.conversation_memory import ConversationMemory
from app.services.cost import estimate_cost


def _percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


@dataclass
class ProviderCost:
    provider: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


@dataclass
class Analytics:
    conversations: int = 0
    messages: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_by_provider: list[ProviderCost] = field(default_factory=list)
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    top_documents: list[dict] = field(default_factory=list)
    feedback_up: int = 0
    feedback_down: int = 0


class AnalyticsService:
    def __init__(self, db: Session, org_id: str) -> None:
        self._db = db
        self._org_id = org_id

    def _assistant_messages(self) -> list[Message]:
        stmt = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(User, User.id == Conversation.user_id)
            .where(User.org_id == self._org_id, Message.role == "assistant")
        )
        return list(self._db.execute(stmt).scalars().all())

    def compute(self) -> Analytics:
        messages = self._assistant_messages()

        conv_count = self._db.execute(
            select(func.count())
            .select_from(Conversation)
            .join(User, User.id == Conversation.user_id)
            .where(User.org_id == self._org_id)
        ).scalar_one()

        by_provider: dict[str, list[int]] = {}
        latencies: list[int] = []
        doc_counter: Counter[str] = Counter()
        tokens_in = tokens_out = 0

        for m in messages:
            tokens_in += m.tokens_in
            tokens_out += m.tokens_out
            latencies.append(m.latency_ms)
            provider = m.provider or "unknown"
            agg = by_provider.setdefault(provider, [0, 0])
            agg[0] += m.tokens_in
            agg[1] += m.tokens_out
            for c in ConversationMemory.serialize_citations(m.citations):
                if isinstance(c, dict) and c.get("document_id"):
                    doc_counter[c["document_id"]] += 1

        cost_by_provider = [
            ProviderCost(
                provider=p,
                tokens_in=ti,
                tokens_out=to,
                cost_usd=round(estimate_cost(p, ti, to), 6),
            )
            for p, (ti, to) in sorted(by_provider.items())
        ]

        top_documents = self._resolve_top_documents(doc_counter)
        up, down = self._feedback_counts()

        return Analytics(
            conversations=conv_count,
            messages=len(messages),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_by_provider=cost_by_provider,
            latency_p50_ms=round(_percentile(latencies, 0.50), 1),
            latency_p95_ms=round(_percentile(latencies, 0.95), 1),
            latency_p99_ms=round(_percentile(latencies, 0.99), 1),
            top_documents=top_documents,
            feedback_up=up,
            feedback_down=down,
        )

    def _resolve_top_documents(self, counter: Counter[str], limit: int = 5) -> list[dict]:
        out: list[dict] = []
        for doc_id, count in counter.most_common(limit):
            doc = self._db.get(Document, doc_id)
            out.append(
                {
                    "document_id": doc_id,
                    "filename": doc.filename if doc else None,
                    "retrievals": count,
                }
            )
        return out

    def _feedback_counts(self) -> tuple[int, int]:
        stmt = (
            select(Feedback.rating, func.count())
            .join(Message, Message.id == Feedback.message_id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(User, User.id == Conversation.user_id)
            .where(User.org_id == self._org_id)
            .group_by(Feedback.rating)
        )
        up = down = 0
        for rating, count in self._db.execute(stmt).all():
            if rating > 0:
                up += count
            else:
                down += count
        return up, down

    def queue_monitor(self) -> dict[str, dict[str, int]]:
        """Ingestion job counts by status and by stage, org-scoped."""
        by_status: dict[str, int] = {}
        by_stage: dict[str, int] = {}
        stmt = (
            select(IngestionJob.status, IngestionJob.stage, func.count())
            .join(Document, Document.id == IngestionJob.document_id)
            .where(Document.org_id == self._org_id)
            .group_by(IngestionJob.status, IngestionJob.stage)
        )
        for status, stage, count in self._db.execute(stmt).all():
            by_status[status] = by_status.get(status, 0) + count
            by_stage[stage] = by_stage.get(stage, 0) + count
        return {"by_status": by_status, "by_stage": by_stage}
