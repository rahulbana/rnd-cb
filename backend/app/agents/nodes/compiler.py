"""Compiler agent: synthesises final study tips from all specialist output."""
from __future__ import annotations

from app.agents import llm
from app.agents.nodes.base import timed_node
from app.agents.prompts import compiler_prompt
from app.agents.state import PlanState
from app.schemas import StudyTips


@timed_node("compiler")
async def compiler_node(state: PlanState) -> PlanState:
    module_titles = ", ".join(m.title for m in state["curriculum"].modules) or "n/a"
    system, user = compiler_prompt(state["request"], state["outline"], module_titles)
    tips = await llm.run_structured(system, user, StudyTips, temperature=0.5)
    return {"study_tips": tips.tips}
