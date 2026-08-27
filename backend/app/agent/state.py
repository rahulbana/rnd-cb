"""Graph state and structured-output schemas for the research agent.

The state is the single source of truth that LangGraph checkpoints to Postgres
after every node. Because it is persisted, keep it JSON-serializable (plain
dicts/lists/str/int/bool) — no live objects.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Reducers
# --------------------------------------------------------------------------- #
def merge_sources(
    existing: list[dict] | None, new: list[dict] | None
) -> list[dict]:
    """Accumulate sources across iterations, de-duplicated by URL, order-stable."""
    by_url: dict[str, dict] = {}
    for bucket in (existing or [], new or []):
        for src in bucket:
            url = src.get("url")
            if url and url not in by_url:
                by_url[url] = src
    return list(by_url.values())


# --------------------------------------------------------------------------- #
# Structured LLM outputs
# --------------------------------------------------------------------------- #
class ResearchPlan(BaseModel):
    """Output of the planning node."""

    sub_questions: list[str] = Field(
        description="3-6 focused sub-questions that decompose the topic.",
        default_factory=list,
    )
    initial_queries: list[str] = Field(
        description="Concrete web-search queries to start with.",
        default_factory=list,
    )


class Reflection(BaseModel):
    """Output of the reflection node — the loop's continue/stop decision."""

    is_sufficient: bool = Field(
        description="True if gathered findings adequately answer the topic."
    )
    knowledge_gaps: list[str] = Field(
        default_factory=list,
        description="Specific gaps still unanswered. Empty when sufficient.",
    )
    follow_up_queries: list[str] = Field(
        default_factory=list,
        description="New search queries to close the gaps. Empty when sufficient.",
    )


# --------------------------------------------------------------------------- #
# Graph state
# --------------------------------------------------------------------------- #
class ResearchState(TypedDict, total=False):
    # Inputs
    topic: str
    max_iterations: int
    max_queries_per_iteration: int

    # Planning
    plan: list[str]

    # Iterative research
    pending_queries: list[str]
    executed_queries: Annotated[list[str], operator.add]
    findings: Annotated[list[str], operator.add]
    sources: Annotated[list[dict], merge_sources]
    knowledge_gaps: list[str]
    iteration: int
    is_complete: bool

    # Output
    final_report: str
