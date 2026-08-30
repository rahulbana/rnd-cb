"""Weather tool.

Real data from **Open-Meteo** (keyless):
  * dates within the forecast horizon  → live daily forecast   (trust=LIVE)
  * dates further out                  → historical archive for the same month
                                         last year, averaged     (trust=RECENT)
  * API unreachable / offline          → seasonal climate table (trust=ESTIMATED)

Per spec section 8 we never present a seasonal estimate as the live/current
forecast — the trust label always reflects the true source.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..config.settings import get_settings
from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult
from .geocode import resolve_coords
from .http import get_json

_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Seasonal fallback (only when the API is unreachable).
_SEASON_TABLE = {
    "winter": {"high": 8, "low": 1, "rain": "moderate"},
    "spring": {"high": 18, "low": 8, "rain": "moderate"},
    "summer": {"high": 29, "low": 19, "rain": "low"},
    "autumn": {"high": 17, "low": 9, "rain": "moderate"},
}
_MONTH_TO_SEASON = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring",
                    5: "spring", 6: "summer", 7: "summer", 8: "summer",
                    9: "autumn", 10: "autumn", 11: "autumn"}


def _rain_label(prob: float | None) -> str:
    if prob is None:
        return "unknown"
    if prob >= 60:
        return "high"
    if prob >= 30:
        return "moderate"
    return "low"


class WeatherTool(Tool):
    name = "weather"
    description = "Weather outlook for a destination (Open-Meteo live/historical)."

    async def run(self, *, destination: str, month: int | None = None,
                  start_date: str | None = None, **_: object) -> ToolResult:
        settings = get_settings()
        month = month or 6
        if settings.enable_live_data:
            coords = await resolve_coords(destination)
            if coords:
                live = await self._from_api(destination, coords, month, start_date)
                if live is not None:
                    return live
        return self._fallback(destination, month)

    async def _from_api(self, destination: str, coords: dict, month: int,
                        start_date: str | None) -> ToolResult | None:
        target = self._target_date(month, start_date)
        horizon = (target - date.today()).days

        if 0 <= horizon <= 14:
            data = await get_json(_FORECAST_URL, params={
                "latitude": coords["lat"], "longitude": coords["lng"],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": coords.get("timezone", "auto"),
                "start_date": target.isoformat(),
                "end_date": (target + timedelta(days=min(6, 14 - horizon))).isoformat(),
            }, ttl=3 * 3600)
            trust, fresh, source = DataTrust.LIVE, Freshness.HOURS, "open-meteo/forecast"
        else:
            # Typical values: same month, previous year (historical archive).
            year = date.today().year - 1
            first = date(year, month, 1)
            last = date(year, month, 28)
            data = await get_json(_ARCHIVE_URL, params={
                "latitude": coords["lat"], "longitude": coords["lng"],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": coords.get("timezone", "auto"),
                "start_date": first.isoformat(), "end_date": last.isoformat(),
            }, ttl=30 * 24 * 3600)
            trust, fresh, source = DataTrust.RECENT, Freshness.DAYS, "open-meteo/archive"

        daily = (data or {}).get("daily") or {}
        highs = [v for v in daily.get("temperature_2m_max", []) if v is not None]
        lows = [v for v in daily.get("temperature_2m_min", []) if v is not None]
        probs = [v for v in daily.get("precipitation_probability_max", []) if v is not None]
        if not highs or not lows:
            return None

        avg_high = round(sum(highs) / len(highs), 1)
        avg_low = round(sum(lows) / len(lows), 1)
        avg_prob = round(sum(probs) / len(probs)) if probs else None
        return ToolResult(
            tool=self.name, ok=True, trust=trust, freshness=fresh, source=source,
            data={
                "destination": destination,
                "season": _MONTH_TO_SEASON.get(month, "summer"),
                "typical_high_c": avg_high, "typical_low_c": avg_low,
                "rain_probability": _rain_label(avg_prob),
                "rain_probability_pct": avg_prob,
            },
        )

    @staticmethod
    def _target_date(month: int, start_date: str | None) -> date:
        if start_date:
            try:
                return date.fromisoformat(start_date[:10])
            except ValueError:
                pass
        today = date.today()
        year = today.year if month >= today.month else today.year + 1
        return date(year, month, 15)

    def _fallback(self, destination: str, month: int) -> ToolResult:
        season = _MONTH_TO_SEASON.get(month, "summer")
        base = _SEASON_TABLE[season]
        return ToolResult(
            tool=self.name, ok=True,
            trust=DataTrust.ESTIMATED, freshness=Freshness.STATIC, source="climate-table",
            data={
                "destination": destination, "season": season,
                "typical_high_c": base["high"], "typical_low_c": base["low"],
                "rain_probability": base["rain"],
            },
        )
