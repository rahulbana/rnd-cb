"""Declarative registry of agents.

The graph, the progress labels and the streaming layer all derive from this
single source of truth, so adding a specialist agent is a one-line change.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.agents.nodes import (
    assessment_node,
    compiler_node,
    curriculum_node,
    planner_node,
    quiz_node,
    resources_node,
    scheduler_node,
)
from app.agents.nodes.base import NodeFn


@dataclass(frozen=True)
class AgentSpec:
    id: str  # graph node id (must NOT collide with a PlanState key)
    label: str  # user-facing progress label
    node: NodeFn
    role: str  # "lead" | "specialist" | "compiler"


LEAD = AgentSpec(
    "planner", "🧭 Lead Planner — designing the plan & delegating", planner_node, "lead"
)

SPECIALISTS: list[AgentSpec] = [
    AgentSpec(
        "curriculum_agent",
        "📚 Curriculum Agent — building learning modules",
        curriculum_node,
        "specialist",
    ),
    AgentSpec(
        "scheduler_agent",
        "🗓️ Scheduler Agent — laying out your timetable",
        scheduler_node,
        "specialist",
    ),
    AgentSpec(
        "resources_agent",
        "🔗 Resources Agent — curating materials",
        resources_node,
        "specialist",
    ),
    AgentSpec(
        "assessment_agent",
        "✅ Assessment Agent — creating checkpoints",
        assessment_node,
        "specialist",
    ),
    AgentSpec(
        "quiz_agent",
        "📝 Quiz Agent — researching board papers & building questions",
        quiz_node,
        "specialist",
    ),
]

COMPILER = AgentSpec(
    "compiler", "🧩 Lead Coach — assembling your study plan", compiler_node, "compiler"
)

ALL_AGENTS: list[AgentSpec] = [LEAD, *SPECIALISTS, COMPILER]

# Convenience lookups derived from the registry.
AGENT_LABELS: dict[str, str] = {a.id: a.label for a in ALL_AGENTS}
SPECIALIST_IDS: list[str] = [a.id for a in SPECIALISTS]
