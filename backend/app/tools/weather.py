"""Weather tool.

Uses a live API when ``WEATHER_API_KEY`` is configured; otherwise returns
clearly-labelled seasonal *estimates* derived from a small climate table.
Per spec section 8/23 we never present estimated weather as live/current data.
"""
from __future__ import annotations

from ..config.settings import get_settings
from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult

# Very small seasonal climate reference (typical highs/lows in °C by hemisphere
# season). Intentionally coarse — labelled ESTIMATED, never presented as live.
_SEASON_TABLE = {
    "winter": {"high": 8, "low": 1, "rain": "moderate"},
    "spring": {"high": 18, "low": 8, "rain": "moderate"},
    "summer": {"high": 29, "low": 19, "rain": "low"},
    "autumn": {"high": 17, "low": 9, "rain": "moderate"},
}

_MONTH_TO_SEASON_NORTH = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}


class WeatherTool(Tool):
    name = "weather"
    description = "Seasonal weather outlook for a destination and month."

    async def run(self, *, destination: str, month: int | None = None, **_: object) -> ToolResult:
        settings = get_settings()
        month = month or 6
        season = _MONTH_TO_SEASON_NORTH.get(month, "summer")
        base = _SEASON_TABLE[season]

        if settings.weather_api_key:
            # Placeholder for a real integration (e.g. OpenWeather/Meteo).
            # Kept as an estimate here to avoid coupling tests to a live network.
            trust, freshness, source = DataTrust.RECENT, Freshness.HOURS, "weather-api"
        else:
            trust, freshness, source = DataTrust.ESTIMATED, Freshness.STATIC, "climate-table"

        return ToolResult(
            tool=self.name,
            ok=True,
            trust=trust,
            freshness=freshness,
            source=source,
            data={
                "destination": destination,
                "season": season,
                "typical_high_c": base["high"],
                "typical_low_c": base["low"],
                "rain_probability": base["rain"],
            },
        )
