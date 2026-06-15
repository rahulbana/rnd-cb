"""Scheduler agent: lays out a realistic week-by-week schedule."""
from __future__ import annotations

from app.agents import llm
from app.agents.nodes.base import timed_node
from app.agents.prompts import scheduler_prompt
from app.agents.state import PlanState
from app.schemas import ScheduleOutput


@timed_node("scheduler")
async def scheduler_node(state: PlanState) -> PlanState:
    system, user = scheduler_prompt(state["request"], state["outline"])
    schedule = await llm.run_structured(system, user, ScheduleOutput, temperature=0.3)
    return {"schedule": schedule}
