"""Geocode / maps tool.

Returns coordinates for well-known destinations from a small built-in gazetteer
so map features work offline. A real geocoding API can be swapped in behind the
same interface when ``MAPS_API_KEY`` is set.
"""
from __future__ import annotations

from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult

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


class GeocodeTool(Tool):
    name = "geocode"
    description = "Resolve a place name to latitude/longitude coordinates."

    async def run(self, *, query: str, **_: object) -> ToolResult:
        key = query.strip().lower()
        for name, (lat, lng) in _GAZETTEER.items():
            if name in key:
                return ToolResult(
                    tool=self.name,
                    ok=True,
                    trust=DataTrust.VERIFIED,
                    freshness=Freshness.STATIC,
                    source="gazetteer",
                    data={"query": query, "lat": lat, "lng": lng, "matched": name},
                )
        return ToolResult(
            tool=self.name, ok=False, source="gazetteer",
            error=f"no coordinates found for '{query}'",
        )
