"""Flight search tool.

Produces *estimated* route/price envelopes from great-circle distance rather
than live availability. Per spec section 8 we never fabricate live flight
availability — results are explicitly labelled ESTIMATED.
"""
from __future__ import annotations

import math

from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult
from .geocode import _GAZETTEER


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _lookup(city: str) -> tuple[float, float] | None:
    key = city.strip().lower()
    for name, coords in _GAZETTEER.items():
        if name in key:
            return coords
    return None


class FlightSearchTool(Tool):
    name = "flight_search"
    description = "Estimate flight duration and price range between two cities."

    async def run(self, *, origin: str, destination: str, travelers: int = 1, **_: object) -> ToolResult:
        a, b = _lookup(origin), _lookup(destination)
        if not a or not b:
            return self._fail(f"unknown airport city in '{origin}' -> '{destination}'")
        distance = _haversine_km(a, b)
        # Rough cruise 800 km/h + ~1.5h airport overhead.
        duration_hours = round(distance / 800 + 1.5, 1)
        # Very rough economy fare band, USD, one traveller.
        base = 60 + distance * 0.09
        low = round(base * 0.8)
        high = round(base * 1.7)
        stops = 0 if distance < 6000 else 1
        return ToolResult(
            tool=self.name,
            ok=True,
            trust=DataTrust.ESTIMATED,
            freshness=Freshness.STATIC,
            source="distance-model",
            data={
                "origin": origin,
                "destination": destination,
                "distance_km": round(distance),
                "duration_hours": duration_hours,
                "stops": stops,
                "price_low_usd": low * travelers,
                "price_high_usd": high * travelers,
                "travelers": travelers,
            },
        )
