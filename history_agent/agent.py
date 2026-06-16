"""The research agent: drives an OpenAI model with web search to find events.

The agent uses the OpenAI Responses API and its built-in ``web_search`` tool so
the model can actually browse the internet — searching websites, news archives
and reference material — rather than relying only on memorised facts.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .dateparse import ParsedDate

# Default model. Override with the OPENAI_MODEL environment variable or --model.
DEFAULT_MODEL = "gpt-4o"

# The built-in web search tool changed names across API versions. We try the
# current name first and transparently fall back to the older preview name.
_WEB_SEARCH_TOOL_TYPES = ("web_search", "web_search_preview")

_SYSTEM_INSTRUCTIONS = """\
You are a meticulous historical researcher. You have a web search tool — USE IT
liberally to verify facts against multiple reputable sources (encyclopedias,
news archives, official records, sports statistics sites) instead of relying on
memory. Prefer primary and well-known secondary sources, and be honest about
uncertainty.

Produce a well-organised Markdown report. Cover a broad range of categories
where relevant:
- Politics, government and major national/world events
- Wars, disasters and landmark legal or social milestones
- Science, technology and space
- Sports (e.g. notable Test matches and cricket, Olympic events, world records)
- Arts, cinema, music and culture
- Notable births and deaths (including celebrities and public figures)

Give special attention to events in India, but cover globally significant
events from any country too. For every notable item, include the year (when the
input has no year), a one-to-three sentence description, and the location/country.
At the end, add a "Sources" section listing the URLs you relied on.
If you genuinely cannot find notable events for a category, say so briefly rather
than inventing anything."""


@dataclass
class ResearchResult:
    """The outcome of a research run."""

    markdown: str
    model: str
    used_web_search: bool


def build_prompt(parsed: ParsedDate, country: str | None = None) -> str:
    """Construct the user prompt sent to the model for a parsed date."""
    focus = ""
    if country:
        focus = (
            f"\nFocus especially on events relevant to {country}, but still "
            "include globally significant events from elsewhere."
        )

    if parsed.has_year:
        return (
            f"Research what important and noteworthy things happened on "
            f"{parsed.human()} (this exact date). Search the web to find "
            f"significant events, milestones, and notable births or deaths that "
            f"occurred specifically on that day.{focus}\n\n"
            f"Title the report: \"On This Day — {parsed.human()}\"."
        )

    return (
        f"Research what historically happened on {parsed.human()} across all "
        f"years (a 'this day in history' overview). Search the web to find "
        f"significant events, milestones, famous births and deaths, sporting "
        f"moments and cultural events that occurred on {parsed.human()} in any "
        f"year. Organise the findings clearly, ideally grouped by category and, "
        f"within each, ordered by year.{focus}\n\n"
        f"Title the report: \"This Day in History — {parsed.human()}\"."
    )


def _build_client(api_key: str | None):
    """Create an OpenAI client, with a friendly error if the SDK is missing."""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - exercised only without the dep
        raise RuntimeError(
            "The 'openai' package is not installed. Run: pip install -r requirements.txt"
        ) from exc

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "No OpenAI API key found. Set the OPENAI_API_KEY environment variable "
            "(or pass api_key=...)."
        )
    return OpenAI(api_key=key)


def research_date(
    parsed: ParsedDate,
    *,
    country: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> ResearchResult:
    """Run the research agent for a parsed date and return a Markdown report.

    Args:
        parsed: The structured date to research.
        country: Optional country to emphasise in the research.
        model: OpenAI model id. Falls back to OPENAI_MODEL then DEFAULT_MODEL.
        api_key: OpenAI API key. Falls back to the OPENAI_API_KEY env var.

    Returns:
        A :class:`ResearchResult`.

    Raises:
        RuntimeError: If the SDK/API key is missing or the API call fails.
    """
    client = _build_client(api_key)
    model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
    prompt = build_prompt(parsed, country=country)

    last_error: Exception | None = None
    for tool_type in _WEB_SEARCH_TOOL_TYPES:
        try:
            response = client.responses.create(
                model=model,
                tools=[{"type": tool_type}],
                instructions=_SYSTEM_INSTRUCTIONS,
                input=prompt,
            )
            return ResearchResult(
                markdown=response.output_text.strip(),
                model=model,
                used_web_search=True,
            )
        except Exception as exc:  # noqa: BLE001 - we inspect and may retry/fall back
            last_error = exc
            if _is_unsupported_tool_error(exc):
                # This tool name isn't available; try the next candidate name.
                continue
            break

    # As a last resort, run without web search so the user still gets an answer,
    # clearly flagged as un-searched. If even that fails, surface the error.
    try:
        response = client.responses.create(
            model=model,
            instructions=_SYSTEM_INSTRUCTIONS,
            input=prompt
            + "\n\n(Note: web search is unavailable; answer from your own "
            "knowledge and clearly state that results were not web-verified.)",
        )
        return ResearchResult(
            markdown=response.output_text.strip(),
            model=model,
            used_web_search=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"OpenAI request failed: {exc}") from (last_error or exc)


def _is_unsupported_tool_error(exc: Exception) -> bool:
    """Heuristic: does this error indicate the web search tool name is unknown?"""
    message = str(exc).lower()
    return "tool" in message and (
        "web_search" in message or "unsupported" in message or "unknown" in message
    )
