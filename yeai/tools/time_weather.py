"""Current time, timezone and temperature for a place.

Uses Open-Meteo's free, key-less geocoding and forecast APIs:

* geocoding: https://geocoding-api.open-meteo.com  (name -> lat/lon/timezone)
* forecast:  https://api.open-meteo.com             (lat/lon -> current weather)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from .base import Tool
from .http import get_json

_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST = "https://api.open-meteo.com/v1/forecast"

# A compact subset of WMO weather codes for human-friendly descriptions.
_WEATHER_CODES: Dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def _geocode(place: str) -> Dict[str, Any]:
    data = get_json(_GEOCODE, params={"name": place, "count": 1, "language": "en"})
    results = data.get("results") or []
    if not results:
        raise ValueError(f"Could not find a location named {place!r}.")
    return results[0]


def _time_and_weather(place: str) -> str:
    loc = _geocode(place)
    lat = loc["latitude"]
    lon = loc["longitude"]
    label_parts = [loc.get("name", place)]
    if loc.get("admin1"):
        label_parts.append(loc["admin1"])
    if loc.get("country"):
        label_parts.append(loc["country"])
    label = ", ".join(label_parts)

    forecast = get_json(
        _FORECAST,
        params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "timezone": "auto",
        },
    )

    current = forecast.get("current_weather", {}) or {}
    temp = current.get("temperature")
    windspeed = current.get("windspeed")
    code = current.get("weathercode")
    condition = _WEATHER_CODES.get(int(code), "unknown") if code is not None else "unknown"

    tz_name = forecast.get("timezone", loc.get("timezone", "UTC"))
    tz_abbr = forecast.get("timezone_abbreviation", "")
    offset_seconds = int(forecast.get("utc_offset_seconds", 0) or 0)

    # Compute the local wall-clock time from "now" + the location's UTC offset.
    local_now = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    hours, rem = divmod(abs(offset_seconds), 3600)
    minutes = rem // 60
    sign = "+" if offset_seconds >= 0 else "-"
    offset_str = f"UTC{sign}{hours:02d}:{minutes:02d}"

    temp_str = f"{temp} °C" if temp is not None else "n/a"
    wind_str = f"{windspeed} km/h" if windspeed is not None else "n/a"

    return (
        f"Location: {label} (lat {lat}, lon {lon})\n"
        f"- Local time: {local_now.strftime('%Y-%m-%d %H:%M')} "
        f"({tz_name} {tz_abbr}, {offset_str})\n"
        f"- Timezone: {tz_name} ({offset_str})\n"
        f"- Temperature: {temp_str}\n"
        f"- Conditions: {condition}\n"
        f"- Wind speed: {wind_str}"
    )


TIME_WEATHER_TOOL = Tool(
    name="time_and_weather",
    description=(
        "Get the current local time, timezone (with UTC offset) and current "
        "temperature/weather conditions for a place. Accepts a country name, "
        "a city, or 'City, Country'. Examples: 'Japan', 'London', "
        "'Paris, France'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "place": {
                "type": "string",
                "description": "Country or city to look up (e.g. 'Japan' or 'London').",
            }
        },
        "required": ["place"],
    },
    handler=_time_and_weather,
)

TOOLS = [TIME_WEATHER_TOOL]
