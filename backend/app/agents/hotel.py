"""Hotel / Accommodation Agent (spec section 8)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..llm import TaskComplexity
from ..schemas.agents import AgentResult, AgentStatus, HotelOption
from ..schemas.common import DataPoint, DataTrust, Money, TravelStyle
from .base import AgentContext, BaseAgent
from ._common import GUARDRAILS, primary_destination, request_brief


class _HotelSet(BaseModel):
    options: list[HotelOption] = Field(default_factory=list)


class HotelAgent(BaseAgent):
    name = "hotel"
    description = "Accommodation options across neighborhoods, price bands and traveler fit."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        system = (
            f"{GUARDRAILS} You are a hotel advisor. Suggest 3 accommodation options across "
            "budget/comfort/premium tiers, each with neighborhood, indicative nightly price, "
            "who it suits and key amenities."
        )
        user = f"Recommend accommodation for this trip.\n{request_brief(req)}"
        result, usage, used_llm = await ctx.runtime.generate_structured(
            system=system, user=user, schema=_HotelSet,
            fallback=lambda: self._fallback(dest, req.preferences.travel_style,
                                            req.budget.currency if req.budget else "USD"),
            complexity=TaskComplexity.MODERATE,
        )
        status = AgentStatus.OK if used_llm else AgentStatus.PARTIAL
        return self._result(
            status=status,
            summary=f"{len(result.options)} accommodation options for {dest}.",
            data=result.model_dump(),
            citations=[DataPoint(value="Accommodation suggestions", source="llm" if used_llm else "offline-template",
                                 trust=DataTrust.AI_RECOMMENDATION, confidence=0.5 if used_llm else 0.3)],
            warnings=[] if used_llm else ["Offline mode: generic price tiers; enable AI for named hotels."],
            tokens=usage.total_tokens or None, cost_usd=usage.cost_usd or None,
        )

    @staticmethod
    def _fallback(dest: str, style: TravelStyle, currency: str) -> _HotelSet:
        bands = {"budget": 45, "comfort": 120, "premium": 320}
        return _HotelSet(options=[
            HotelOption(name=f"{dest} budget stay", neighborhood="Central/near transit",
                        rating=3.8, price_per_night=Money(amount=bands["budget"], currency=currency),
                        good_for=["solo", "backpackers"], amenities=["Wi-Fi", "24h reception"]),
            HotelOption(name=f"{dest} comfort hotel", neighborhood="City center",
                        rating=4.3, price_per_night=Money(amount=bands["comfort"], currency=currency),
                        good_for=["couples", "families"], amenities=["Wi-Fi", "Breakfast", "AC"]),
            HotelOption(name=f"{dest} premium hotel", neighborhood="Prime district",
                        rating=4.7, price_per_night=Money(amount=bands["premium"], currency=currency),
                        good_for=["luxury", "business"], amenities=["Spa", "Concierge", "Pool"]),
        ])
