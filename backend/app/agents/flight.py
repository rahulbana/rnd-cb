"""Flight Agent (spec section 8). Uses the flight_search tool for estimates and
never fabricates live availability."""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus, FlightOption
from ..schemas.common import DataPoint, DataTrust, Freshness, Money
from .base import AgentContext, BaseAgent
from ._common import primary_destination


class FlightAgent(BaseAgent):
    name = "flight"
    description = "Estimated flight routes, durations and price bands (not live availability)."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        origin = req.origin
        dest = primary_destination(req)
        if not origin:
            return self._result(
                status=AgentStatus.SKIPPED,
                summary="No origin provided; skipped flight estimation.",
                warnings=["Provide an origin city to estimate flights."],
            )

        tool_res = await ctx.tools.execute(
            "flight_search", origin=origin, destination=dest, travelers=req.travelers
        )
        if not tool_res.ok:
            return self._result(
                status=AgentStatus.PARTIAL, summary="Could not estimate flights.",
                warnings=[tool_res.error or "flight estimation unavailable"],
            )

        d = tool_res.data
        currency = req.budget.currency if req.budget else "USD"
        # The distance model returns USD; keep currency label honest.
        option = FlightOption(
            airline="(various carriers)",
            from_airport=origin,
            to_airport=dest,
            stops=int(d["stops"]),
            duration_hours=float(d["duration_hours"]),
            est_price=Money(amount=float(d["price_low_usd"]), currency="USD"),
            note=f"Estimated economy fare band ${d['price_low_usd']:.0f}–${d['price_high_usd']:.0f} "
                 f"for {req.travelers} traveller(s); ~{d['distance_km']} km.",
        )
        return self._result(
            status=AgentStatus.PARTIAL,  # estimates, not live data
            summary=f"~{d['duration_hours']}h, {d['stops']} stop(s), est. "
                    f"${d['price_low_usd']:.0f}–${d['price_high_usd']:.0f}.",
            data={"options": [option.model_dump()], "currency": currency,
                  "price_band_usd": [d["price_low_usd"], d["price_high_usd"]]},
            citations=[DataPoint(
                value="Flight duration & price estimated from distance model",
                source=tool_res.source, trust=DataTrust.ESTIMATED,
                freshness=Freshness.STATIC, confidence=0.4,
            )],
            warnings=["Flight figures are estimates — verify live availability before booking."],
        )
