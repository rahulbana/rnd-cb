"""Assemble the deep-search agent as a LangGraph state graph."""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .state import AgentState
from .nodes import plan_queries, search, synthesize


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


# Compiled once at import time and reused across requests.
agent_graph = build_graph()
