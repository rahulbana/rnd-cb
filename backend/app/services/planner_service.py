"""Orchestrates the agent graph: one-shot generation and SSE streaming."""
from __future__ import annotations

import json
from typing import AsyncGenerator

from app.agents.graph import build_graph
from app.agents.registry import AGENT_LABELS
from app.agents.state import PlanState
from app.core.logging import get_logger
from app.schemas import QuizOutput, StudyPlan, StudyPlanRequest
from app.services.exporters import render_markdown

log = get_logger("services.planner")


def _assemble_plan(req: StudyPlanRequest, state: PlanState) -> StudyPlan:
    """Build the final StudyPlan from accumulated graph state."""
    plan = StudyPlan(
        request=req,
        outline=state["outline"],
        curriculum=state["curriculum"],
        schedule=state["schedule"],
        resources=state["resources"],
        assessment=state["assessment"],
        quiz=state.get("quiz") or QuizOutput(),
        study_tips=state.get("study_tips", []),
    )
    plan.markdown = render_markdown(plan)
    return plan


async def generate_plan(req: StudyPlanRequest) -> StudyPlan:
    """Run the full graph and return the assembled study plan."""
    log.info("generating plan: grade=%s subject=%s topic=%s", req.grade, req.subject, req.topic)
    graph = build_graph()
    final_state: PlanState = await graph.ainvoke({"request": req})
    plan = _assemble_plan(req, final_state)
    log.info("plan generated: %s (%d quiz questions)", plan.outline.title, plan.quiz.total())
    return plan


def _sse(event: str, payload: dict) -> dict:
    """A dict shaped for sse-starlette's EventSourceResponse.

    Do NOT pre-format the wire here, or sse-starlette double-wraps it.
    """
    return {"event": event, "data": json.dumps(payload)}


async def stream_plan(req: StudyPlanRequest) -> AsyncGenerator[dict, None]:
    """Run the graph, yielding SSE events as agents make progress.

    Event types: 'init', 'agent_done', 'complete', 'error'.
    """
    graph = build_graph()
    accumulated: PlanState = {"request": req}

    yield _sse(
        "init",
        {"agents": [{"id": k, "label": v} for k, v in AGENT_LABELS.items()]},
    )

    try:
        async for update in graph.astream({"request": req}, stream_mode="updates"):
            # `update` maps node-name -> state delta for nodes that just ran.
            for node_name, delta in update.items():
                if isinstance(delta, dict):
                    accumulated.update(delta)
                yield _sse(
                    "agent_done",
                    {"agent": node_name, "label": AGENT_LABELS.get(node_name, node_name)},
                )

        plan = _assemble_plan(req, accumulated)
        yield _sse("complete", {"plan": json.loads(plan.model_dump_json())})
    except Exception as exc:  # surface a clean error to the client
        log.exception("plan streaming failed")
        message = getattr(exc, "message", None) or str(exc)
        yield _sse("error", {"message": message})
