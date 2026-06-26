"""Models for persisted agent runs (the run-history / tracing store)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ..schemas.source import Source


class StepEvent(BaseModel):
    """A single recorded step in a run's lifecycle (token events excluded)."""

    ts: float
    type: str
    node: Optional[str] = None
    tool: Optional[str] = None
    model: Optional[str] = None
    query: Optional[str] = None
    count: Optional[int] = None
    detail: Optional[str] = None
    error: Optional[str] = None


class RunRecord(BaseModel):
    """The full, persisted record of one agent run."""

    id: str
    query: str
    num_subqueries: int
    status: str = "running"  # running | completed | failed | cancelled
    started_at: float
    finished_at: Optional[float] = None
    duration_ms: Optional[int] = None
    subqueries: List[str] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    report: str = ""
    error: Optional[str] = None
    steps: List[StepEvent] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Lightweight projection for the run-list dashboard view."""

    id: str
    query: str
    status: str
    started_at: float
    duration_ms: Optional[int] = None
    num_subqueries: int = 0
    num_sources: int = 0

    @classmethod
    def from_record(cls, r: RunRecord) -> "RunSummary":
        return cls(
            id=r.id,
            query=r.query,
            status=r.status,
            started_at=r.started_at,
            duration_ms=r.duration_ms,
            num_subqueries=len(r.subqueries),
            num_sources=len(r.sources),
        )
