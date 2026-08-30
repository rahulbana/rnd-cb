"""Packing Agent (spec section 8) — deterministic list from weather, duration, activities."""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus
from ..schemas.common import TravelerType
from .base import AgentContext, BaseAgent

_BASE = ["Passport & travel documents", "Phone + charger", "Payment cards & some local cash",
         "Reusable water bottle", "Basic medication & toiletries", "Comfortable walking shoes"]


class PackingAgent(BaseAgent):
    name = "packing"
    description = "Personalised packing list from weather, activities and traveler type."
    depends_on = ("weather",)

    async def _run(self, ctx: AgentContext) -> AgentResult:
        trip = ctx.trip
        req = trip.request
        items = list(_BASE)

        weather = trip.weather or {}
        high = weather.get("typical_high_c")
        low = weather.get("typical_low_c")
        rain = weather.get("rain_probability")
        if isinstance(high, (int, float)) and high >= 27:
            items += ["Light breathable clothing", "Sunglasses & sunscreen", "Sun hat"]
        if isinstance(low, (int, float)) and low <= 10:
            items += ["Warm jacket", "Thermal layers"]
        if rain in ("moderate", "high"):
            items.append("Compact umbrella / rain jacket")

        interests = {i.lower() for i in req.preferences.interests}
        if "photography" in interests:
            items.append("Camera + spare batteries/memory")
        if "beach" in interests or "beaches" in interests:
            items += ["Swimwear", "Quick-dry towel"]
        if "hiking" in interests or "adventure" in interests:
            items.append("Daypack & hiking shoes")

        if req.traveler_type is TravelerType.FAMILY:
            items += ["Kids' essentials & snacks", "Entertainment for children"]

        if (req.duration_days or 0) >= 7:
            items.append("Laundry bag / travel detergent")

        # De-duplicate, preserve order.
        seen: set[str] = set()
        deduped = [i for i in items if not (i in seen or seen.add(i))]

        return self._result(
            status=AgentStatus.OK,
            summary=f"Packing list with {len(deduped)} items.",
            data={"items": deduped},
        )
