"""Native application tools exposed to the LangGraph agent.

These live in the application itself (translation and world-time), and are
combined with the movie tools discovered from the remote MCP server. Each tool's
docstring is the description the LLM reads, and errors are returned as data
(``{"error": ...}``) so the agent can recover gracefully instead of crashing the
run.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool

from . import timetools, translation


@tool
async def translate(
    text: str,
    target_language: str,
    source_language: str = "auto",
) -> dict[str, Any]:
    """Translate text between languages (source auto-detected by default).

    Accepts either ISO 639-1 codes (``en``, ``fr``, ``ja``) or plain language
    names (``english``, ``french``, ``japanese``).

    Args:
        text: The text to translate.
        target_language: Target language as an ISO code ('es') or name ('spanish').
        source_language: Source language, or 'auto' to detect.
    """
    try:
        return await translation.translate_text(text, target_language, source_language)
    except translation.TranslationError as exc:
        return {"error": str(exc)}


@tool
def list_supported_languages() -> dict[str, Any]:
    """Return supported translation languages as a name -> ISO code map."""
    return translation.list_languages()


@tool
def get_current_time(location: str) -> dict[str, Any]:
    """Get the current local date/time and UTC offset for a location.

    Args:
        location: City, country, or IANA timezone, e.g. 'Tokyo' or 'Asia/Tokyo'.
    """
    try:
        return timetools.current_time(location)
    except timetools.TimezoneError as exc:
        return {"error": str(exc)}


@tool
def compare_timezones(location_a: str, location_b: str) -> dict[str, Any]:
    """Compare the current time in two locations and report the hour difference.

    Args:
        location_a: First city/country/timezone.
        location_b: Second city/country/timezone.
    """
    try:
        return timetools.compare_timezones(location_a, location_b)
    except timetools.TimezoneError as exc:
        return {"error": str(exc)}


@tool
def convert_time(time_str: str, from_location: str, to_location: str) -> dict[str, Any]:
    """Convert a wall-clock time (today) from one location's zone to another's.

    Args:
        time_str: A 24-hour time 'HH:MM', e.g. '14:30'.
        from_location: Source city/country/timezone.
        to_location: Target city/country/timezone.
    """
    try:
        return timetools.convert_time(time_str, from_location, to_location)
    except timetools.TimezoneError as exc:
        return {"error": str(exc)}


# Registered with the agent alongside the remote MCP (movie) tools.
LOCAL_TOOLS: list[BaseTool] = [
    translate,
    list_supported_languages,
    get_current_time,
    compare_timezones,
    convert_time,
]

__all__ = ["LOCAL_TOOLS"]
