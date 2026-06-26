"""State schema for the deep-search LangGraph agent."""
from __future__ import annotations

from typing import List, TypedDict

from ..schemas.source import Source


class AgentState(TypedDict, total=False):
    # Input
    query: str
    num_subqueries: int

    # Planning
    subqueries: List[str]

    # Search
    sources: List[Source]

    # Output
    report: str
