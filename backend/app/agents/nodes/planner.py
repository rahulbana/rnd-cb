"""Lead planner agent: creates the outline and delegation briefs."""
from __future__ import annotations

from app.agents import llm
from app.agents.nodes.base import timed_node
from app.agents.prompts import planner_prompt
from app.agents.state import PlanState
from app.schemas import PlanOutline


@timed_node("planner")
async def planner_node(state: PlanState) -> PlanState:
    system, user = planner_prompt(state["request"])
    outline = await llm.run_structured(system, user, PlanOutline, temperature=0.4)
    return {"outline": outline}
