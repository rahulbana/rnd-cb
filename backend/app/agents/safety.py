"""Safety Agent (spec section 8) — practical, non-alarmist safety guidance."""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus, SafetyInfo
from ..schemas.common import DataPoint, DataTrust
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class SafetyAgent(BaseAgent):
    name = "safety"
    description = "Balanced safety guidance: scams, emergency numbers, health, caution areas."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        system = (
            f"{GUARDRAILS} You are a travel-safety advisor. Give balanced, practical guidance — "
            "avoid fear-mongering. Include common scams, emergency numbers, health precautions and "
            "any areas warranting extra caution."
        )
        user = f"Provide safety guidance.\n{request_brief(req)}"
        info, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=SafetyInfo,
            fallback=lambda: SafetyInfo(
                destination=dest,
                overall="Most visits are trouble-free with normal urban precautions.",
                common_scams=["Overpriced taxis", "Distraction pickpocketing in crowds",
                              "Fake tickets from unofficial sellers"],
                emergency_numbers={"general": "check local emergency number on arrival"},
                health=["Carry basic medication", "Drink safe water", "Have travel insurance"],
                caution_areas=["Crowded tourist hotspots (pickpocketing)"],
            ),
        )
        return self._result(
            status=AgentStatus.OK if used_llm else AgentStatus.PARTIAL,
            summary=f"Safety overview for {dest}.",
            data=info.model_dump(),
            citations=[DataPoint(value="Safety guidance", source="llm" if used_llm else "offline-template",
                                 trust=DataTrust.AI_RECOMMENDATION, confidence=0.4)],
            warnings=["Check your government's official travel advisory before departure."],
            tokens=usage.total_tokens or None, cost_usd=usage.cost_usd or None,
        )
