"""Destination Research Agent (spec section 8)."""
from __future__ import annotations

from ..llm import TaskComplexity
from ..schemas.agents import AgentResult, AgentStatus, DestinationOverview
from ..schemas.common import DataPoint, DataTrust
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class DestinationAgent(BaseAgent):
    name = "destination"
    description = "Destination overview, best time to visit, neighborhoods, hidden gems."
    complexity = TaskComplexity.MODERATE

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        system = (
            f"{GUARDRAILS} You are a destination researcher. Provide an overview, the best "
            "time to visit, an ideal duration, top highlights, a few hidden gems, key "
            "neighborhoods and important local customs."
        )
        user = f"Research this trip and describe the primary destination.\n{request_brief(req)}"

        overview, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=DestinationOverview,
            fallback=lambda: self._fallback(dest, req.duration_days or 5),
            complexity=self.complexity,
        )
        status = AgentStatus.OK if used_llm else AgentStatus.PARTIAL
        return self._result(
            status=status,
            summary=f"Destination brief for {overview.destination}.",
            data=overview.model_dump(),
            citations=[DataPoint(
                value=f"Overview of {overview.destination}",
                source="llm" if used_llm else "offline-template",
                trust=DataTrust.AI_RECOMMENDATION,
                confidence=0.6 if used_llm else 0.3,
            )],
            warnings=[] if used_llm else ["Offline mode: generic overview; enable the AI model for specifics."],
            tokens=usage.total_tokens or None,
            cost_usd=usage.cost_usd or None,
        )

    @staticmethod
    def _fallback(dest: str, duration: int) -> DestinationOverview:
        return DestinationOverview(
            destination=dest,
            summary=(
                f"{dest} is a popular destination offering a mix of culture, food and "
                "sightseeing. Detailed, specific guidance requires the AI model to be enabled."
            ),
            best_time_to_visit="Shoulder seasons (spring/autumn) usually balance weather and crowds.",
            ideal_duration_days=max(3, min(duration, 14)),
            highlights=["Main historic center", "A signature landmark", "Local food district"],
            hidden_gems=["A quieter neighborhood away from the main sights"],
            neighborhoods=["City center", "Old town", "Waterfront / park district"],
            local_customs=["Greet politely", "Learn a few local phrases", "Check tipping norms"],
        )
