"""Air quality by city (Open-Meteo Air Quality API, free, no key)."""
from __future__ import annotations

from .base import Tool, err, http_get_json, ok
from .geo import geocode

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _aqi_category(aqi: float | None) -> str:
    if aqi is None:
        return "unknown"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def get_air_quality(city: str) -> dict:
    """Return current air quality indicators for a city."""
    loc = geocode(city)
    if not loc:
        return err(f"Could not find a location named '{city}'.")

    data = http_get_json(
        AQ_URL,
        params={
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "current": "us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,"
                       "sulphur_dioxide,ozone",
            "timezone": "auto",
        },
    )
    cur = data.get("current", {})
    aqi = cur.get("us_aqi")
    return ok({
        "location": f"{loc['name']}, {loc.get('country', '')}".strip(", "),
        "us_aqi": aqi,
        "category": _aqi_category(aqi),
        "pm2_5": cur.get("pm2_5"),
        "pm10": cur.get("pm10"),
        "ozone": cur.get("ozone"),
        "nitrogen_dioxide": cur.get("nitrogen_dioxide"),
        "sulphur_dioxide": cur.get("sulphur_dioxide"),
        "carbon_monoxide": cur.get("carbon_monoxide"),
        "observed_at": cur.get("time"),
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_air_quality",
            description="Get the current air quality (US AQI, PM2.5, PM10, ozone, "
                        "etc.) for a given city name.",
            category="Weather & Environment",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name."},
                },
                "required": ["city"],
            },
            func=get_air_quality,
        )
    ]
