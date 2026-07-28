"""Assemble the research graph.

Topology:

    START → plan → search → read → reflect ─┬─(gaps & budget left)→ search
                                             └─(done/capped)───────→ synthesize → END

The conditional edge after `reflect` is the reflection loop: it sends control
back to `search` for another iteration when gaps remain and budget allows, else
forward to `synthesize`. A `checkpointer` persists state after every node so a
crashed 20-minute run resumes from its last completed step.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    plan_node,
    read_node,
    reflect_node,
    route_after_reflect,
    search_node,
    synthesize_node,
)
from app.graph.state import ResearchState


def build_graph(checkpointer=None):
    """Compile the research graph. Pass a checkpointer for crash recovery."""
    g = StateGraph(ResearchState)

    g.add_node("plan", plan_node)
    g.add_node("search", search_node)
    g.add_node("read", read_node)
    g.add_node("reflect", reflect_node)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "plan")
    g.add_edge("plan", "search")
    g.add_edge("search", "read")
    g.add_edge("read", "reflect")
    g.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"search": "search", "synthesize": "synthesize"},
    )
    g.add_edge("synthesize", END)

    return g.compile(checkpointer=checkpointer)
