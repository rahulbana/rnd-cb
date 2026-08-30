"""Geocode / maps tool.

Primary source: the **Open-Meteo Geocoding API** (keyless, worldwide) — resolves
any place name to real coordinates. Falls back to a small built-in gazetteer so
the feature still works offline or if the API is unreachable.
"""
from __future__ import annotations

from ..config.settings import get_settings
from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult
from .http import get_json

# Offline fallback gazetteer (used only when the live API is unavailable).
_GAZETTEER: dict[str, tuple[float, float]] = {
    "paris": (48.8566, 2.3522),
    "tokyo": (35.6762, 139.6503),
    "kyoto": (35.0116, 135.7681),
    "osaka": (34.6937, 135.5023),
    "london": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "delhi": (28.6139, 77.2090),
    "bali": (-8.3405, 115.0920),
    "rome": (41.9028, 12.4964),
    "barcelona": (41.3874, 2.1686),
    "bangkok": (13.7563, 100.5018),
    "dubai": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
    "sydney": (-33.8688, 151.2093),
    "istanbul": (41.0082, 28.9784),
}

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


async def resolve_coords(query: str) -> dict | None:
    """Return ``{lat, lng, name, timezone, source}`` for a place, or None.

    Shared by the weather and flight tools. Tries the live API first (when
    live data is enabled), then the offline gazetteer.
    """
    settings = get_settings()
    if settings.enable_live_data:
        data = await get_json(
            _GEOCODE_URL,
            params={"name": query, "count": 1, "language": "en", "format": "json"},
            ttl=7 * 24 * 3600,
        )
        if data and data.get("results"):
            r = data["results"][0]
            return {"lat": r["latitude"], "lng": r["longitude"], "name": r.get("name"),
                    "timezone": r.get("timezone", "auto"), "source": "open-meteo"}
    key = query.strip().lower()
    for name, (lat, lng) in _GAZETTEER.items():
        if name in key:
            return {"lat": lat, "lng": lng, "name": name.title(),
                    "timezone": "auto", "source": "gazetteer"}
    return None


class GeocodeTool(Tool):
    name = "geocode"
    description = "Resolve a place name to latitude/longitude coordinates (Open-Meteo)."

    async def run(self, *, query: str, **_: object) -> ToolResult:
        settings = get_settings()
        if settings.enable_live_data:
            live = await self._live(query)
            if live is not None:
                return live
        return self._fallback(query)

    async def _live(self, query: str) -> ToolResult | None:
        data = await get_json(
            _GEOCODE_URL,
            params={"name": query, "count": 1, "language": "en", "format": "json"},
            ttl=7 * 24 * 3600,  # coordinates are stable
        )
        if not data or not data.get("results"):
            return None
        r = data["results"][0]
        return ToolResult(
            tool=self.name, ok=True,
            trust=DataTrust.LIVE, freshness=Freshness.STATIC, source="open-meteo",
            data={
                "query": query, "lat": r["latitude"], "lng": r["longitude"],
                "matched": r.get("name"), "country": r.get("country"),
                "timezone": r.get("timezone"), "population": r.get("population"),
            },
        )

    def _fallback(self, query: str) -> ToolResult:
        key = query.strip().lower()
        for name, (lat, lng) in _GAZETTEER.items():
            if name in key:
                return ToolResult(
                    tool=self.name, ok=True,
                    trust=DataTrust.VERIFIED, freshness=Freshness.STATIC, source="gazetteer",
                    data={"query": query, "lat": lat, "lng": lng, "matched": name},
                )
        return ToolResult(tool=self.name, ok=False, source="gazetteer",
                          error=f"no coordinates found for '{query}'")
