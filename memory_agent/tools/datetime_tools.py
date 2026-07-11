"""Current-time tool resolving IANA zones, cities, and country names."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

import pytz
from langchain_core.tools import tool


def _format_time(label: str, tz: ZoneInfo) -> str:
    now = datetime.now(tz)
    return f"Current time in {label}: {now:%Y-%m-%d %H:%M:%S %Z%z} ({now:%A})"


def make_time_tools() -> list:
    @tool
    def current_time(timezone_or_place: str) -> str:
        """Get the current local time for an IANA timezone, city, or country.

        Examples: "Asia/Kolkata", "Tokyo", "Germany", "UTC".
        """
        q = timezone_or_place.strip()

        # 1) direct IANA timezone (e.g. "Asia/Kolkata", "UTC")
        try:
            return _format_time(q, ZoneInfo(q))
        except Exception:
            pass

        # 2) country name -> timezone(s) via pytz
        code = {n.lower(): c for c, n in pytz.country_names.items()}.get(q.lower())
        if code and pytz.country_timezones.get(code):
            zones = pytz.country_timezones[code]
            out = _format_time(zones[0], ZoneInfo(zones[0]))
            if len(zones) > 1:
                out += f"\n(This country spans {len(zones)} zones: {', '.join(zones)})"
            return out

        # 3) city / fuzzy match against IANA zone names
        key = q.lower().replace(" ", "_")
        matches = [
            z for z in available_timezones()
            if key == z.split("/")[-1].lower() or key in z.lower()
        ]
        if matches:
            best = sorted(matches, key=len)[0]
            return _format_time(best, ZoneInfo(best))

        return (
            f"Couldn't resolve '{timezone_or_place}' to a timezone. "
            "Try an IANA name like 'Europe/Paris' or a country/city name."
        )

    return [current_time]
