"""State schema for the deep-search LangGraph agent."""
from __future__ import annotations

from typing import Annotated, List, TypedDict
import operator


class Source(TypedDict):
    title: str
    url: str
    content: str
    subquery: str


class SearchResult(TypedDict):
    subquery: str
    sources: List[Source]


class AgentState(TypedDict, total=False):
    # Input
    query: str
    num_subqueries: int

    # Planning
    subqueries: List[str]

    # Search (reducer appends results as parallel/sequential searches complete)
    search_results: Annotated[List[SearchResult], operator.add]
    sources: List[Source]

    # Output
    report: str
