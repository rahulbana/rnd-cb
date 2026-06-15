"""Builds the LangGraph multi-agent workflow.

Flow:
    START -> planner -> {curriculum, scheduler, resources, assessment} -> compiler -> END

The planner (lead agent) runs first and delegates. The four specialist agents
fan out and run in parallel, then the compiler merges everything.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    assessment_node,
    compiler_node,
    curriculum_node,
    planner_node,
    quiz_node,
    resources_node,
    scheduler_node,
)
from app.agents.state import PlanState

# Friendly, user-facing labels for each node — surfaced as live progress.
# Node IDs intentionally avoid clashing with PlanState keys (LangGraph forbids
# a node name that matches a state key).
AGENT_LABELS: dict[str, str] = {
    "planner": "🧭 Lead Planner — designing the plan & delegating",
    "curriculum_agent": "📚 Curriculum Agent — building learning modules",
    "scheduler_agent": "🗓️ Scheduler Agent — laying out your timetable",
    "resources_agent": "🔗 Resources Agent — curating materials",
    "assessment_agent": "✅ Assessment Agent — creating checkpoints",
    "quiz_agent": "📝 Quiz Agent — researching board papers & building questions",
    "compiler": "🧩 Lead Coach — assembling your study plan",
}

SPECIALISTS = [
    "curriculum_agent",
    "scheduler_agent",
    "resources_agent",
    "assessment_agent",
    "quiz_agent",
]


@lru_cache
def build_graph():
    """Compile and cache the study-plan agent graph."""
    graph = StateGraph(PlanState)

    graph.add_node("planner", planner_node)
    graph.add_node("curriculum_agent", curriculum_node)
    graph.add_node("scheduler_agent", scheduler_node)
    graph.add_node("resources_agent", resources_node)
    graph.add_node("assessment_agent", assessment_node)
    graph.add_node("quiz_agent", quiz_node)
    graph.add_node("compiler", compiler_node)

    graph.add_edge(START, "planner")

    # Lead planner delegates to all specialists (parallel fan-out).
    for specialist in SPECIALISTS:
        graph.add_edge("planner", specialist)
        graph.add_edge(specialist, "compiler")

    graph.add_edge("compiler", END)

    return graph.compile()
