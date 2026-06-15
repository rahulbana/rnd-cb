"""Runs the agent graph and exposes both streaming and one-shot APIs."""
from __future__ import annotations

import json
from typing import AsyncGenerator

from app.agents.graph import AGENT_LABELS, build_graph
from app.agents.state import PlanState
from app.schemas import QuizOutput, StudyPlan, StudyPlanRequest
from app.services.export import render_markdown


def _assemble_plan(req: StudyPlanRequest, state: PlanState) -> StudyPlan:
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
    graph = build_graph()
    final_state: PlanState = await graph.ainvoke({"request": req})
    return _assemble_plan(req, final_state)


async def stream_plan(req: StudyPlanRequest) -> AsyncGenerator[dict, None]:
    """Run the graph, yielding Server-Sent Events as agents make progress.

    Each yielded dict is formatted into a proper SSE frame by sse-starlette's
    EventSourceResponse (do NOT pre-format the wire here, or it gets
    double-wrapped). Event types: 'init', 'agent_done', 'complete', 'error'.
    """
    graph = build_graph()
    accumulated: PlanState = {"request": req}

    def sse(event: str, payload: dict) -> dict:
        return {"event": event, "data": json.dumps(payload)}

    # Announce the agents that will participate.
    yield sse(
        "init",
        {
            "agents": [
                {"id": key, "label": label} for key, label in AGENT_LABELS.items()
            ]
        },
    )

    try:
        async for update in graph.astream({"request": req}, stream_mode="updates"):
            # `update` maps node-name -> state delta for nodes that just ran.
            for node_name, delta in update.items():
                if isinstance(delta, dict):
                    accumulated.update(delta)
                yield sse(
                    "agent_done",
                    {
                        "agent": node_name,
                        "label": AGENT_LABELS.get(node_name, node_name),
                    },
                )

        plan = _assemble_plan(req, accumulated)
        yield sse("complete", {"plan": json.loads(plan.model_dump_json())})
    except Exception as exc:  # surface a clean error to the client
        yield sse("error", {"message": str(exc)})
