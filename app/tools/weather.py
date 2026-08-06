"""Current temperature / weather by city (Open-Meteo, free, no key)."""
from __future__ import annotations

from .base import Tool, err, http_get_json, ok
from .geo import geocode

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def get_current_temperature(city: str, units: str = "celsius") -> dict:
    """Return current temperature and basic weather for a city."""
    loc = geocode(city)
    if not loc:
        return err(f"Could not find a location named '{city}'.")

    temp_unit = "fahrenheit" if units.lower().startswith("f") else "celsius"
    data = http_get_json(
        FORECAST_URL,
        params={
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "wind_speed_10m,weather_code",
            "temperature_unit": temp_unit,
            "timezone": "auto",
        },
    )
    cur = data.get("current", {})
    unit_symbol = "°F" if temp_unit == "fahrenheit" else "°C"
    return ok({
        "location": f"{loc['name']}, {loc.get('country', '')}".strip(", "),
        "temperature": cur.get("temperature_2m"),
        "unit": unit_symbol,
        "feels_like": cur.get("apparent_temperature"),
        "humidity_percent": cur.get("relative_humidity_2m"),
        "wind_speed": cur.get("wind_speed_10m"),
        "observed_at": cur.get("time"),
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_current_temperature",
            description="Get the current temperature and basic weather (humidity, "
                        "wind, feels-like) for a given city name.",
            category="Weather & Environment",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. 'Mumbai'."},
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature units. Defaults to celsius.",
                    },
                },
                "required": ["city"],
            },
            func=get_current_temperature,
        )
    ]
