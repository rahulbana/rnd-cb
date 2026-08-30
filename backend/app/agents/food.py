"""Restaurant / Food Agent (spec section 8)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..schemas.agents import AgentResult, AgentStatus, PlaceRec
from ..schemas.common import DataPoint, DataTrust, Recommendation
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class _Food(BaseModel):
    items: list[PlaceRec] = Field(default_factory=list)


class FoodAgent(BaseAgent):
    name = "food"
    description = "Restaurants, local specialties and dietary-aware dining suggestions."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        dietary = ", ".join(req.preferences.dietary) or "no specific restrictions"
        system = (
            f"{GUARDRAILS} You are a food advisor. Suggest 5-6 dining ideas spanning price levels, "
            "including local specialties and options honoring the traveller's dietary needs. "
            "Give a reason and a rough price level for each."
        )
        user = f"Recommend food & restaurants. Dietary: {dietary}.\n{request_brief(req)}"
        result, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=_Food,
            fallback=lambda: self._fallback(dest, req.preferences.dietary),
        )
        status = AgentStatus.OK if used_llm else AgentStatus.PARTIAL
        return self._result(
            status=status,
            summary=f"{len(result.items)} dining ideas for {dest}.",
            data=result.model_dump(),
            citations=[DataPoint(value="Dining recommendations", source="llm" if used_llm else "offline-template",
                                 trust=DataTrust.AI_RECOMMENDATION, confidence=0.5 if used_llm else 0.3)],
            warnings=[] if used_llm else ["Offline mode: generic dining categories."],
            tokens=usage.total_tokens or None, cost_usd=usage.cost_usd or None,
        )

    @staticmethod
    def _fallback(dest: str, dietary: list[str]) -> _Food:
        veg = any(d in {"vegetarian", "vegan"} for d in dietary)
        items = [
            PlaceRec(name=f"{dest} local specialty spot", category="restaurant",
                     why="Try the signature regional dish.", recommendation=Recommendation.MUST_SEE),
            PlaceRec(name="Central food market", category="street_food",
                     why="Affordable variety and local flavor.", recommendation=Recommendation.HIGHLY_RECOMMENDED),
            PlaceRec(name="Well-rated mid-range bistro", category="restaurant",
                     why="Comfortable sit-down dinner.", recommendation=Recommendation.HIGHLY_RECOMMENDED),
            PlaceRec(name="Cozy cafe / breakfast", category="cafe",
                     why="Good start to the day.", recommendation=Recommendation.OPTIONAL),
        ]
        if veg:
            items.append(PlaceRec(name="Vegetarian/vegan-friendly eatery", category="restaurant",
                                  why="Dedicated plant-based menu.", recommendation=Recommendation.HIGHLY_RECOMMENDED))
        return _Food(items=items)
