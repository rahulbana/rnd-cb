"""Flight search tool.

Two modes:
  * **Amadeus** (real offers) when ``AMADEUS_CLIENT_ID/SECRET`` are configured —
    resolves cities to IATA codes and fetches live flight offers (trust=LIVE).
  * **Distance model** otherwise — duration/price estimated from great-circle
    distance using *real worldwide geocoding* (Open-Meteo), so it works for any
    city, clearly labelled ESTIMATED. Per spec section 8 we never present an
    estimate as live availability.
"""
from __future__ import annotations

import math
import time

from ..config.settings import get_settings
from ..schemas.common import DataTrust, Freshness
from .base import Tool, ToolResult
from .geocode import resolve_coords
from .http import get_json, post_json

# --- Amadeus OAuth token cache ---------------------------------------------
_token: dict = {"value": None, "expires_at": 0.0}


async def _amadeus_token(base: str, client_id: str, client_secret: str) -> str | None:
    if _token["value"] and _token["expires_at"] > time.time() + 30:
        return _token["value"]
    data = await post_json(
        f"{base}/v1/security/oauth2/token",
        data={"grant_type": "client_credentials",
              "client_id": client_id, "client_secret": client_secret},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if not data or "access_token" not in data:
        return None
    _token["value"] = data["access_token"]
    _token["expires_at"] = time.time() + int(data.get("expires_in", 1800))
    return _token["value"]


async def _iata_for(base: str, token: str, city: str) -> str | None:
    data = await get_json(
        f"{base}/v1/reference-data/locations",
        params={"subType": "AIRPORT,CITY", "keyword": city, "page[limit]": 1},
        headers={"Authorization": f"Bearer {token}"}, ttl=7 * 24 * 3600,
    )
    results = (data or {}).get("data") or []
    return results[0].get("iataCode") if results else None


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


class FlightSearchTool(Tool):
    name = "flight_search"
    description = "Real flight offers (Amadeus) or a geocoded distance-based estimate."

    async def run(self, *, origin: str, destination: str, travelers: int = 1,
                  departure_date: str | None = None, currency: str = "USD", **_: object) -> ToolResult:
        settings = get_settings()

        if settings.enable_live_data and settings.amadeus_client_id and settings.amadeus_client_secret:
            live = await self._amadeus(settings, origin, destination, travelers,
                                       departure_date, currency)
            if live is not None:
                return live

        return await self._estimate(origin, destination, travelers)

    async def _amadeus(self, settings, origin, destination, travelers,
                       departure_date, currency) -> ToolResult | None:
        base = settings.amadeus_base_url
        token = await _amadeus_token(base, settings.amadeus_client_id, settings.amadeus_client_secret)
        if not token or not departure_date:
            return None
        o_iata = await _iata_for(base, token, origin)
        d_iata = await _iata_for(base, token, destination)
        if not o_iata or not d_iata:
            return None
        offers = await get_json(
            f"{base}/v2/shopping/flight-offers",
            params={"originLocationCode": o_iata, "destinationLocationCode": d_iata,
                    "departureDate": departure_date[:10], "adults": max(1, travelers),
                    "currencyCode": currency, "max": 5},
            headers={"Authorization": f"Bearer {token}"}, ttl=1800,
        )
        data = (offers or {}).get("data") or []
        if not data:
            return None
        options = []
        for off in data[:5]:
            itin = off["itineraries"][0]
            segs = itin["segments"]
            options.append({
                "airline": segs[0].get("carrierCode", "??"),
                "from_airport": o_iata, "to_airport": d_iata,
                "stops": len(segs) - 1,
                "duration": itin.get("duration", ""),
                "price": {"amount": float(off["price"]["total"]),
                          "currency": off["price"].get("currency", currency)},
            })
        cheapest = min(options, key=lambda o: o["price"]["amount"])
        return ToolResult(
            tool=self.name, ok=True, trust=DataTrust.LIVE, freshness=Freshness.HOURS,
            source="amadeus",
            data={"mode": "live", "origin": origin, "destination": destination,
                  "iata": [o_iata, d_iata], "options": options,
                  "cheapest_price": cheapest["price"], "travelers": travelers},
        )

    async def _estimate(self, origin: str, destination: str, travelers: int) -> ToolResult:
        a = await resolve_coords(origin)
        b = await resolve_coords(destination)
        if not a or not b:
            return self._fail(f"could not locate '{origin}' or '{destination}'")
        distance = _haversine_km((a["lat"], a["lng"]), (b["lat"], b["lng"]))
        duration_hours = round(distance / 800 + 1.5, 1)
        base = 60 + distance * 0.09
        low, high = round(base * 0.8), round(base * 1.7)
        stops = 0 if distance < 6000 else 1
        return ToolResult(
            tool=self.name, ok=True, trust=DataTrust.ESTIMATED, freshness=Freshness.STATIC,
            source="distance-model",
            data={"mode": "estimate", "origin": origin, "destination": destination,
                  "distance_km": round(distance), "duration_hours": duration_hours,
                  "stops": stops, "price_low_usd": low * travelers,
                  "price_high_usd": high * travelers, "travelers": travelers},
        )
