"""Assemble the deep-search agent as a LangGraph state graph.

    plan_queries -> search -> synthesize
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .nodes import plan_queries, search, synthesize
from .state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("plan_queries", plan_queries)
    graph.add_node("search", search)
    graph.add_node("synthesize", synthesize)

    graph.add_edge(START, "plan_queries")
    graph.add_edge("plan_queries", "search")
    graph.add_edge("search", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


@lru_cache
def get_graph():
    """Compiled graph, built once and reused across requests."""
    return build_graph()
