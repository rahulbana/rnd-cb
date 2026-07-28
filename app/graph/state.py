"""LangGraph state definition and reducers.

State is a TypedDict so LangGraph can checkpoint it to Postgres between every
super-step. The `sources` channel uses a custom reducer that merges and
re-deduplicates on each write, so accumulating sources across iterations never
reintroduces duplicates. Everything in state must be JSON/msgpack-serializable
for the checkpointer — hence Pydantic models rather than opaque objects.
"""

from __future__ import annotations

from typing import Annotated, Any, Protocol

from typing_extensions import TypedDict

from app.budget import BudgetTracker
from app.dedup import deduplicate
from app.models.report import ResearchReport
from app.models.schemas import ProgressEvent, ResearchRequest, Source, SubQuestion


class ProgressEmitter(Protocol):
    """Injected via graph config so nodes can stream progress without owning I/O."""

    def __call__(self, event: ProgressEvent) -> None: ...


def merge_sources(existing: list[Source], new: list[Source]) -> list[Source]:
    """Reducer: append new sources, then dedup keeping most-credible copies."""
    combined = list(existing) + list(new)
    combined.sort(key=lambda s: s.credibility, reverse=True)
    return deduplicate(combined)


def replace(_existing: Any, new: Any) -> Any:
    """Reducer: last write wins (used for scalar/whole-object channels)."""
    return new


class ResearchState(TypedDict, total=False):
    # Inputs / identity
    job_id: str
    request: ResearchRequest

    # Planning
    sub_questions: Annotated[list[SubQuestion], replace]
    current_queries: Annotated[list[str], replace]

    # Evidence
    sources: Annotated[list[Source], merge_sources]

    # Control
    budget: Annotated[BudgetTracker, replace]
    iteration: Annotated[int, replace]
    gaps: Annotated[list[str], replace]
    stop_reason: Annotated[str | None, replace]

    # Output
    report: Annotated[ResearchReport | None, replace]
