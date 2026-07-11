"""LangGraph shared state.

The state is a ``TypedDict`` threaded through every node.  Fields that need
to *accumulate* across research iterations use ``operator.add`` reducers;
all other fields are replaced by the returning node.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from deep_agent.models.schemas import (
    FactCheckResult,
    ReflectionResult,
    ResearchPlan,
    ResearchReport,
    ScrapedDocument,
    SearchResult,
)


class ResearchState(TypedDict, total=False):
    """State object passed between LangGraph nodes."""

    # --- Inputs ---------------------------------------------------------
    topic: str
    max_iterations: int

    # --- Planner --------------------------------------------------------
    plan: ResearchPlan

    # --- Loop control ---------------------------------------------------
    pending_queries: list[str]        # queries to run this round (replaced)
    iteration: int

    # --- Search / collect (per-round, replaced) -------------------------
    latest_results: list[SearchResult]
    collected: list[SearchResult]

    # --- Accumulators (added across rounds) -----------------------------
    all_results: Annotated[list[SearchResult], operator.add]
    scraped: Annotated[list[ScrapedDocument], operator.add]
    scraped_urls: Annotated[list[str], operator.add]

    # --- Reflection -----------------------------------------------------
    reflection: ReflectionResult

    # --- Fact checking --------------------------------------------------
    fact_checks: list[FactCheckResult]

    # --- Output ---------------------------------------------------------
    report: ResearchReport
