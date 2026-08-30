"""Budget Agent (spec section 8 & deliverable 15 — the budget engine).

Deterministic and explainable: it assembles minimum/comfort/premium budgets
from the flight, hotel, activity and duration data already in TripState, then
checks feasibility against the user's stated budget. Uses the currency tool to
normalise the USD flight estimate into the trip currency.
"""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus
from ..schemas.common import DataPoint, DataTrust, Money
from ..schemas.trip import BudgetBreakdown, BudgetLine
from .base import AgentContext, BaseAgent

# Per-person / per-day tier estimates by category, in trip currency-neutral USD.
_FOOD_PER_DAY = {"min": 18, "comfort": 45, "premium": 95}
_LOCAL_TRANSPORT_PER_DAY = {"min": 5, "comfort": 14, "premium": 35}
_ACTIVITY_PER_DAY = {"min": 10, "comfort": 30, "premium": 80}
_MISC_FLAT = {"min": 40, "comfort": 100, "premium": 250}


class BudgetAgent(BaseAgent):
    name = "budget"
    description = "Detailed min/comfort/premium budget with feasibility check."
    depends_on = ("activity", "flight", "hotel")

    async def _run(self, ctx: AgentContext) -> AgentResult:
        trip = ctx.trip
        req = trip.request
        currency = req.budget.currency if req.budget else "USD"
        days = max(1, req.duration_days or 3)
        nights = max(1, days - 1)
        travelers = req.travelers

        fx = await self._usd_to(ctx, currency)  # multiply USD amounts by this

        lines: list[BudgetLine] = []

        # --- Flights ---------------------------------------------------------
        if trip.flights and trip.flights.get("mode") == "live" and trip.flights.get("options"):
            # Live offers are already priced in the trip currency (no FX needed).
            prices = sorted(o["est_price"]["amount"] for o in trip.flights["options"])
            f_min = prices[0]
            f_comfort = prices[len(prices) // 2]
            f_premium = prices[-1] * 1.2
            lines.append(self._line("Flights", f_min, f_comfort, f_premium, currency,
                                    "Live offers (round trip may need separate booking)."))
        elif trip.flights and trip.flights.get("price_band_usd"):
            low, high = trip.flights["price_band_usd"]
            lines.append(self._line("Flights", low * fx, (low + high) / 2 * fx, high * 1.4 * fx,
                                    currency, "Round-trip estimate for all travellers."))

        # --- Accommodation ---------------------------------------------------
        if trip.accommodation and trip.accommodation.get("options"):
            opts = trip.accommodation["options"]
            prices = [o["price_per_night"]["amount"] for o in opts]
            prices.sort()
            a_min = prices[0] * nights
            a_comfort = prices[len(prices) // 2] * nights
            a_premium = prices[-1] * nights
            lines.append(self._line("Accommodation", a_min, a_comfort, a_premium, currency,
                                    f"{nights} night(s)."))

        # --- Per-day, per-person categories ---------------------------------
        def per_day(table: dict[str, float]) -> tuple[float, float, float]:
            return (table["min"] * days * travelers * fx,
                    table["comfort"] * days * travelers * fx,
                    table["premium"] * days * travelers * fx)

        lines.append(self._line("Food", *per_day(_FOOD_PER_DAY), currency))
        lines.append(self._line("Local transport", *per_day(_LOCAL_TRANSPORT_PER_DAY), currency))
        lines.append(self._line("Activities", *per_day(_ACTIVITY_PER_DAY), currency))
        lines.append(self._line("Misc / shopping / insurance",
                                _MISC_FLAT["min"] * travelers * fx,
                                _MISC_FLAT["comfort"] * travelers * fx,
                                _MISC_FLAT["premium"] * travelers * fx, currency))

        total_min = sum(l.minimum.amount for l in lines)
        total_comfort = sum(l.comfort.amount for l in lines)
        total_premium = sum(l.premium.amount for l in lines)

        within = advice = None
        advice_list: list[str] = []
        if req.budget:
            within = req.budget.amount >= total_comfort
            if req.budget.amount < total_min:
                advice_list.append("Your budget is below the estimated minimum — consider fewer days, "
                                   "a nearer destination, or cheaper accommodation.")
            elif not within:
                advice_list.append("Budget covers a minimal trip but not the comfort tier — trim "
                                   "premium activities or shorten the stay to stay comfortable.")
            else:
                headroom = req.budget.amount - total_comfort
                advice_list.append(f"Budget looks comfortable with ~{headroom:,.0f} {currency} of headroom.")

        breakdown = BudgetBreakdown(
            currency=currency, lines=lines,
            total_minimum=Money(amount=round(total_min), currency=currency),
            total_comfort=Money(amount=round(total_comfort), currency=currency),
            total_premium=Money(amount=round(total_premium), currency=currency),
            within_budget=within, advice=advice_list,
        )
        return self._result(
            status=AgentStatus.OK,
            summary=f"Comfort budget ~{total_comfort:,.0f} {currency} "
                    f"(min {total_min:,.0f} / premium {total_premium:,.0f}).",
            data=breakdown.model_dump(),
            citations=[DataPoint(value="Budget assembled from estimates", source="budget-engine",
                                 trust=DataTrust.ESTIMATED, confidence=0.45)],
            warnings=["All figures are planning estimates, not quotes."],
        )

    async def _usd_to(self, ctx: AgentContext, currency: str) -> float:
        if currency.upper() == "USD":
            return 1.0
        res = await ctx.tools.execute("currency", amount=1.0, from_currency="USD", to_currency=currency)
        if res.ok:
            return float(res.data["converted"])
        return 1.0

    @staticmethod
    def _line(cat: str, mn: float, cm: float, pr: float, currency: str, note: str | None = None) -> BudgetLine:
        return BudgetLine(
            category=cat,
            minimum=Money(amount=round(mn), currency=currency),
            comfort=Money(amount=round(cm), currency=currency),
            premium=Money(amount=round(pr), currency=currency),
            note=note,
        )
