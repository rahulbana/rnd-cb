"""Curriculum agent: breaks the topic into modules and objectives."""
from __future__ import annotations

from app.agents import llm
from app.agents.nodes.base import timed_node
from app.agents.prompts import curriculum_prompt
from app.agents.state import PlanState
from app.schemas import CurriculumOutput


@timed_node("curriculum")
async def curriculum_node(state: PlanState) -> PlanState:
    system, user = curriculum_prompt(state["request"], state["outline"])
    curriculum = await llm.run_structured(system, user, CurriculumOutput, temperature=0.3)
    return {"curriculum": curriculum}
