"""Assemble the LangGraph research graph.

Topology:

    START -> plan -> search -> reflect --(gaps?)--> search
                                   |
                                   +--(sufficient / budget)--> synthesize -> END

The compiled graph is bound to a Postgres checkpointer so every step is durable:
a long-running run survives process restarts and can be resumed by thread_id.
"""
from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    plan_node,
    reflect_node,
    route_after_reflect,
    search_node,
    synthesize_node,
)
from app.agent.state import ResearchState


def build_graph(checkpointer: BaseCheckpointSaver):
    builder = StateGraph(ResearchState)

    builder.add_node("plan", plan_node)
    builder.add_node("search", search_node)
    builder.add_node("reflect", reflect_node)
    builder.add_node("synthesize", synthesize_node)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "search")
    builder.add_edge("search", "reflect")
    builder.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"search": "search", "synthesize": "synthesize"},
    )
    builder.add_edge("synthesize", END)

    return builder.compile(checkpointer=checkpointer)
