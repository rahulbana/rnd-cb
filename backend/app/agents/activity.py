"""Activity Agent (spec section 8) — ranked attractions and things to do."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..schemas.agents import AgentResult, AgentStatus, PlaceRec
from ..schemas.common import DataPoint, DataTrust, Recommendation
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class _Activities(BaseModel):
    items: list[PlaceRec] = Field(default_factory=list)


class ActivityAgent(BaseAgent):
    name = "activity"
    description = "Attractions, tours, museums and experiences ranked by priority."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        system = (
            f"{GUARDRAILS} You are an activities planner. Suggest 6-8 things to do, each ranked "
            "(must_see / highly_recommended / optional / hidden_gem) with a one-line reason, "
            "rough cost, and typical visit duration. Tailor to the stated interests."
        )
        user = f"Recommend activities for this trip.\n{request_brief(req)}"
        result, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=_Activities,
            fallback=lambda: self._fallback(dest, req.preferences.interests),
        )
        status = AgentStatus.OK if used_llm else AgentStatus.PARTIAL
        return self._result(
            status=status,
            summary=f"{len(result.items)} activities for {dest}.",
            data=result.model_dump(),
            citations=[DataPoint(value="Activity recommendations", source="llm" if used_llm else "offline-template",
                                 trust=DataTrust.AI_RECOMMENDATION, confidence=0.5 if used_llm else 0.3)],
            warnings=[] if used_llm else ["Offline mode: generic categories; enable AI for specific venues."],
            tokens=usage.total_tokens or None, cost_usd=usage.cost_usd or None,
        )

    @staticmethod
    def _fallback(dest: str, interests: list[str]) -> _Activities:
        seed = [
            ("Historic old town walk", "sightseeing", Recommendation.MUST_SEE, 120),
            ("Top museum or gallery", "culture", Recommendation.HIGHLY_RECOMMENDED, 150),
            ("Signature landmark & viewpoint", "sightseeing", Recommendation.MUST_SEE, 90),
            ("Local market food crawl", "food", Recommendation.HIGHLY_RECOMMENDED, 90),
            ("Neighborhood photo walk", "photography", Recommendation.OPTIONAL, 120),
            ("Quiet local park or garden", "nature", Recommendation.HIDDEN_GEM, 90),
        ]
        items = [
            PlaceRec(name=f"{dest}: {name}", category=cat, why=f"Popular for {cat} lovers.",
                     recommendation=rec, duration_minutes=dur)
            for name, cat, rec, dur in seed
        ]
        return _Activities(items=items)
