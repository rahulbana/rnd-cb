"""Flight Agent (spec section 8).

Uses the flight_search tool, which returns either real Amadeus offers (when
configured) or a geocoded distance-based estimate. Never fabricates live
availability — the trust label reflects the actual source.
"""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus, FlightOption
from ..schemas.common import DataPoint, DataTrust, Freshness, Money
from .base import AgentContext, BaseAgent
from ._common import primary_destination


class FlightAgent(BaseAgent):
    name = "flight"
    description = "Flight routes, durations and prices (live via Amadeus, else estimated)."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        origin = req.origin
        dest = primary_destination(req)
        if not origin:
            return self._result(
                status=AgentStatus.SKIPPED,
                summary="No origin provided; skipped flight lookup.",
                warnings=["Provide an origin city to search flights."],
            )

        currency = req.budget.currency if req.budget else "USD"
        tool_res = await ctx.tools.execute(
            "flight_search", origin=origin, destination=dest, travelers=req.travelers,
            departure_date=req.start_date.isoformat() if req.start_date else None,
            currency=currency,
        )
        if not tool_res.ok:
            return self._result(
                status=AgentStatus.PARTIAL, summary="Could not look up flights.",
                warnings=[tool_res.error or "flight lookup unavailable"],
            )

        d = tool_res.data
        if d.get("mode") == "live":
            return self._live_result(d, tool_res.source)
        return self._estimate_result(d, req.travelers, currency, tool_res.source)

    def _live_result(self, d: dict, source: str) -> AgentResult:
        options = [
            FlightOption(
                airline=o["airline"], from_airport=o["from_airport"], to_airport=o["to_airport"],
                stops=int(o["stops"]),
                duration_hours=_iso_hours(o.get("duration", "")),
                est_price=Money(amount=o["price"]["amount"], currency=o["price"]["currency"]),
                note=f"Live offer via {source}.",
            )
            for o in d.get("options", [])
        ]
        cheapest = d.get("cheapest_price", {})
        price = Money(amount=cheapest.get("amount", 0), currency=cheapest.get("currency", "USD"))
        return self._result(
            status=AgentStatus.OK,
            summary=f"{len(options)} live offers, cheapest {price.amount:.0f} {price.currency}.",
            data={"options": [o.model_dump() for o in options], "mode": "live",
                  "cheapest_price": {"amount": price.amount, "currency": price.currency}},
            citations=[DataPoint(value="Live flight offers", source=source,
                                 trust=DataTrust.LIVE, freshness=Freshness.HOURS, confidence=0.9)],
        )

    def _estimate_result(self, d: dict, travelers: int, currency: str, source: str) -> AgentResult:
        option = FlightOption(
            airline="(various carriers)", from_airport=d["origin"], to_airport=d["destination"],
            stops=int(d["stops"]), duration_hours=float(d["duration_hours"]),
            est_price=Money(amount=float(d["price_low_usd"]), currency="USD"),
            note=f"Estimated economy fare band ${d['price_low_usd']:.0f}–${d['price_high_usd']:.0f} "
                 f"for {travelers} traveller(s); ~{d['distance_km']} km.",
        )
        return self._result(
            status=AgentStatus.PARTIAL,
            summary=f"~{d['duration_hours']}h, {d['stops']} stop(s), est. "
                    f"${d['price_low_usd']:.0f}–${d['price_high_usd']:.0f}.",
            data={"options": [option.model_dump()], "currency": currency, "mode": "estimate",
                  "price_band_usd": [d["price_low_usd"], d["price_high_usd"]]},
            citations=[DataPoint(value="Flight duration & price estimated from distance",
                                 source=source, trust=DataTrust.ESTIMATED,
                                 freshness=Freshness.STATIC, confidence=0.4)],
            warnings=["Flight figures are estimates — verify live availability before booking."],
        )


def _iso_hours(iso_duration: str) -> float:
    """Parse an ISO-8601 duration like 'PT13H35M' into hours."""
    if not iso_duration.startswith("PT"):
        return 0.0
    hours = minutes = 0
    num = ""
    for ch in iso_duration[2:]:
        if ch.isdigit():
            num += ch
        elif ch == "H":
            hours = int(num or 0); num = ""
        elif ch == "M":
            minutes = int(num or 0); num = ""
    return round(hours + minutes / 60, 1)
