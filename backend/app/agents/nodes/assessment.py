"""Assessment agent: designs checkpoints and assessments."""
from __future__ import annotations

from app.agents import llm
from app.agents.nodes.base import timed_node
from app.agents.prompts import assessment_prompt
from app.agents.state import PlanState
from app.schemas import AssessmentOutput


@timed_node("assessment")
async def assessment_node(state: PlanState) -> PlanState:
    system, user = assessment_prompt(state["request"], state["outline"])
    assessment = await llm.run_structured(system, user, AssessmentOutput, temperature=0.4)
    return {"assessment": assessment}
