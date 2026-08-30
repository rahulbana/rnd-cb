"""Points-of-interest tool (attractions, food) via **OpenTripMap** (free key).

Returns real, named places near a destination when ``OPENTRIPMAP_API_KEY`` is
set; otherwise reports unavailable so agents fall back to LLM/heuristic
suggestions. Data is labelled LIVE with OpenTripMap/OSM as the source.
"""
from __future__ import annotations

from ..config.settings import get_settings
from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult
from .geocode import resolve_coords
from .http import get_json

_RADIUS_URL = "https://api.opentripmap.com/0.1/en/places/radius"

# Map a logical category to OpenTripMap "kinds".
_KINDS = {
    "attractions": "interesting_places,cultural,historic,architecture,museums",
    "food": "foods",
    "nature": "natural,gardens_and_parks",
}


class PlacesTool(Tool):
    name = "places"
    description = "Real nearby attractions/food via OpenTripMap (requires API key)."

    def available(self) -> bool:
        settings = get_settings()
        return bool(settings.enable_live_data and settings.opentripmap_api_key)

    async def run(self, *, destination: str, kind: str = "attractions",
                  limit: int = 12, radius_m: int = 20000, **_: object) -> ToolResult:
        settings = get_settings()
        if not self.available():
            return ToolResult(tool=self.name, ok=False, source="opentripmap",
                              error="OPENTRIPMAP_API_KEY not configured")
        coords = await resolve_coords(destination)
        if not coords:
            return self._fail(f"could not locate '{destination}'")

        data = await get_json(_RADIUS_URL, params={
            "radius": radius_m, "lon": coords["lng"], "lat": coords["lat"],
            "kinds": _KINDS.get(kind, _KINDS["attractions"]),
            "rate": "2", "format": "json", "limit": limit,
            "apikey": settings.opentripmap_api_key,
        }, ttl=24 * 3600)
        if data is None:
            return self._fail("OpenTripMap request failed")

        places = []
        for f in data:
            name = (f.get("name") or "").strip()
            if not name:
                continue
            places.append({
                "name": name,
                "kinds": f.get("kinds", ""),
                "lat": f.get("point", {}).get("lat"),
                "lng": f.get("point", {}).get("lon"),
                "xid": f.get("xid"),
            })
        return ToolResult(
            tool=self.name, ok=True, trust=DataTrust.LIVE, freshness=Freshness.DAYS,
            source="opentripmap/osm",
            data={"destination": destination, "kind": kind, "places": places},
        )
