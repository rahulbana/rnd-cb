"""Weather Agent (spec section 8) — never hallucinates current weather.

Uses the weather tool for a seasonal outlook and layers concise clothing/risk
advice on top, keeping provenance from the tool.
"""
from __future__ import annotations

from ..schemas.agents import AgentResult, AgentStatus, WeatherOutlook
from ..schemas.common import DataPoint, DataTrust, Freshness
from .base import AgentContext, BaseAgent
from ._common import month_of, primary_destination


class WeatherAgent(BaseAgent):
    name = "weather"
    description = "Seasonal weather outlook with clothing and risk guidance."

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        tool_res = await ctx.tools.execute("weather", destination=dest, month=month_of(req))
        if not tool_res.ok:
            return self._result(status=AgentStatus.PARTIAL, summary="Weather outlook unavailable.",
                                warnings=[tool_res.error or "weather tool failed"])
        d = tool_res.data
        high, low = d["typical_high_c"], d["typical_low_c"]
        clothing = self._clothing(high, low)
        outlook = WeatherOutlook(
            destination=dest, season=d["season"],
            typical_high_c=high, typical_low_c=low,
            rain_probability=d["rain_probability"], clothing=clothing,
            risks=self._risks(d["rain_probability"], high, low),
        )
        trust = DataTrust.RECENT if tool_res.source == "weather-api" else DataTrust.ESTIMATED
        return self._result(
            status=AgentStatus.PARTIAL,
            summary=f"{d['season'].title()} outlook: ~{low}–{high}°C, {d['rain_probability']} rain.",
            data=outlook.model_dump(),
            citations=[DataPoint(value="Seasonal weather outlook", source=tool_res.source,
                                 trust=trust, freshness=Freshness(tool_res.freshness), confidence=0.4)],
            warnings=["Seasonal estimate — check a live forecast close to travel."],
        )

    @staticmethod
    def _clothing(high: float, low: float) -> list[str]:
        out: list[str] = []
        if high >= 27:
            out += ["Light, breathable clothing", "Sun protection", "Reusable water bottle"]
        if low <= 10:
            out += ["Warm layers", "A jacket"]
        if 10 < low < 20:
            out.append("A light layer for evenings")
        out.append("Comfortable walking shoes")
        return out

    @staticmethod
    def _risks(rain: str, high: float, low: float) -> list[str]:
        risks: list[str] = []
        if rain in ("moderate", "high"):
            risks.append("Pack a compact umbrella / rain jacket")
        if high >= 32:
            risks.append("Heat: plan indoor activities midday")
        if low <= 2:
            risks.append("Cold snaps possible")
        return risks
