"""Shared geocoding helper (Open-Meteo geocoding API, free, no key)."""
from __future__ import annotations

from .base import http_get_json

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode(city: str) -> dict | None:
    """Resolve a city/place name to coordinates and metadata.

    Returns a dict with keys: name, country, latitude, longitude, timezone —
    or None if nothing matched.
    """
    data = http_get_json(GEOCODE_URL, params={"name": city, "count": 1, "language": "en"})
    results = data.get("results") or []
    if not results:
        return None
    r = results[0]
    return {
        "name": r.get("name"),
        "country": r.get("country"),
        "admin1": r.get("admin1"),
        "latitude": r.get("latitude"),
        "longitude": r.get("longitude"),
        "timezone": r.get("timezone"),
    }
