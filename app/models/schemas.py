"""Core domain models shared across the graph, API, and job layers."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ResearchDepth(str, Enum):
    quick = "quick"        # 1-2 iterations, tight budget
    standard = "standard"  # default
    deep = "deep"          # max iterations, wider fan-out


class ResearchRequest(BaseModel):
    """A request to research a topic and produce an analyst report."""

    topic: str = Field(..., min_length=3, max_length=500)
    audience: str = Field(
        default="a consulting firm's client",
        description="Who the report is written for — shapes tone and depth.",
    )
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Optional angles to emphasize (e.g. 'competitive moat', 'unit economics').",
    )
    depth: ResearchDepth = ResearchDepth.standard
    max_iterations: int | None = Field(default=None, ge=1, le=10)
    max_usd_cost: float | None = Field(default=None, gt=0)


class SearchHit(BaseModel):
    """A raw result returned by a search backend, before dedup/scoring."""

    title: str
    url: str
    snippet: str = ""
    backend: str = "unknown"
    published: str | None = None
    raw_score: float | None = None


class Source(BaseModel):
    """A deduplicated, scored, and (optionally) read source."""

    id: str = ""
    title: str
    url: str
    snippet: str = ""
    content: str = ""  # full/extracted text once the read node has run
    backend: str = "unknown"
    published: str | None = None
    credibility: float = Field(default=0.5, ge=0.0, le=1.0)
    domain: str = ""
    read: bool = False
    added_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def _default_id(self) -> Source:
        # Derive a stable id from the URL. Must run *after* fields are set so
        # `url` is populated (a before-validator on `id` cannot see `url`, since
        # `id` is declared first). Object mutation here is fine on a fresh model.
        if not self.id:
            self.id = hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:12]
        return self

    @classmethod
    def from_hit(cls, hit: SearchHit) -> Source:
        return cls(
            title=hit.title,
            url=hit.url,
            snippet=hit.snippet,
            backend=hit.backend,
            published=hit.published,
        )


class SubQuestion(BaseModel):
    """A planned research sub-question with lifecycle state."""

    id: str
    question: str
    rationale: str = ""
    status: Literal["open", "searched", "answered", "gap"] = "open"
    findings: str = ""
    source_ids: list[str] = Field(default_factory=list)


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    killed_budget = "killed_budget"  # stopped by iteration/cost cap


class ProgressEvent(BaseModel):
    """A streamed progress update (serialized as an SSE `data:` payload)."""

    job_id: str
    phase: str          # e.g. "plan", "search", "read", "reflect", "synthesize"
    message: str
    iteration: int = 0
    sources_found: int = 0
    usd_spent: float = 0.0
    status: JobStatus = JobStatus.running
    ts: datetime = Field(default_factory=_utcnow)
    data: dict[str, Any] = Field(default_factory=dict)
