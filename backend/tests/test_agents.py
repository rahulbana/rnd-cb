"""Tests for the agent graph and plan orchestration."""
from __future__ import annotations

from app.agents.graph import build_graph
from app.agents.registry import AGENT_LABELS, SPECIALIST_IDS
from app.services.planner_service import generate_plan, stream_plan


def test_graph_has_all_agents():
    nodes = set(build_graph().get_graph().nodes.keys())
    for agent_id in AGENT_LABELS:
        assert agent_id in nodes
    # No node id may collide with a PlanState key (LangGraph forbids this).
    assert "quiz_agent" in SPECIALIST_IDS


async def test_generate_plan(stub_llm, no_research, sample_request):
    plan = await generate_plan(sample_request)
    assert plan.outline.title == "Mastering Quadratics"
    assert plan.curriculum.modules and plan.schedule.weeks
    assert plan.resources.resources and plan.assessment.assessments
    assert plan.quiz.total() > 0
    assert plan.study_tips
    assert plan.markdown.startswith("# Mastering Quadratics")


async def test_stream_plan_emits_lifecycle(stub_llm, no_research, sample_request):
    events = [chunk["event"] for chunk in [e async for e in stream_plan(sample_request)]]
    assert events[0] == "init"
    assert events[-1] == "complete"
    assert events.count("agent_done") == len(AGENT_LABELS)
