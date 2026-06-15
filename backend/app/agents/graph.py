"""Builds the LangGraph multi-agent workflow from the agent registry.

Flow:
    START -> planner -> {specialists...} -> compiler -> END

The planner (lead agent) runs first and delegates. The specialist agents fan
out and run in parallel, then the compiler merges everything.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.registry import ALL_AGENTS, COMPILER, LEAD, SPECIALISTS
from app.agents.state import PlanState


@lru_cache
def build_graph() -> CompiledStateGraph:
    """Compile and cache the study-plan agent graph."""
    graph = StateGraph(PlanState)

    for spec in ALL_AGENTS:
        graph.add_node(spec.id, spec.node)

    graph.add_edge(START, LEAD.id)
    for spec in SPECIALISTS:
        graph.add_edge(LEAD.id, spec.id)  # lead delegates (parallel fan-out)
        graph.add_edge(spec.id, COMPILER.id)  # each specialist feeds the compiler
    graph.add_edge(COMPILER.id, END)

    return graph.compile()
