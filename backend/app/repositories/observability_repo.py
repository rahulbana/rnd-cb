"""Observability repository — persists agent runs for metrics/tracing (section 29)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.tables import AgentRun
from ..schemas.agents import AgentResult


class ObservabilityRepository:
    def record_runs(self, session: Session, *, trip_id: str | None, run_id: str,
                    results: list[AgentResult], model: str | None) -> None:
        for r in results:
            session.add(AgentRun(
                trip_id=trip_id, run_id=run_id, agent_name=r.agent,
                status=r.status.value, model=model, latency_ms=r.latency_ms,
                tokens=r.tokens, cost_usd=r.cost_usd, error=r.error,
            ))
        session.flush()

    def summary(self, session: Session) -> dict:
        total = session.scalar(select(func.count()).select_from(AgentRun)) or 0
        tokens = session.scalar(select(func.coalesce(func.sum(AgentRun.tokens), 0))) or 0
        cost = session.scalar(select(func.coalesce(func.sum(AgentRun.cost_usd), 0.0))) or 0.0
        avg_latency = session.scalar(select(func.coalesce(func.avg(AgentRun.latency_ms), 0))) or 0
        return {
            "total_agent_runs": int(total),
            "total_tokens": int(tokens),
            "total_cost_usd": round(float(cost), 4),
            "avg_latency_ms": round(float(avg_latency), 1),
        }


observability_repository = ObservabilityRepository()
