"""Resources agent: recommends learning resources."""
from __future__ import annotations

from app.agents import llm
from app.agents.nodes.base import timed_node
from app.agents.prompts import resources_prompt
from app.agents.state import PlanState
from app.schemas import ResourcesOutput


@timed_node("resources")
async def resources_node(state: PlanState) -> PlanState:
    system, user = resources_prompt(state["request"], state["outline"])
    resources = await llm.run_structured(system, user, ResourcesOutput, temperature=0.4)
    return {"resources": resources}
