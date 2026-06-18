"""The agents: a researcher and an independent verifier, both driven by an OpenAI
model with the built-in ``web_search`` tool.

The pipeline is two stages:

1. :func:`research_date` — a researcher browses the web and drafts a report.
2. :func:`verify_report` — a *separate* fact-checking agent independently
   re-searches the web, confirms or corrects each claim, and consolidates the
   list of sources before anything is shown to the user.
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

_RESEARCHER_INSTRUCTIONS = """\
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

SOURCES ARE MANDATORY. End the report with a "## Sources" section: a numbered
list where each entry is a Markdown link to the exact page you used, in the form
`1. [Page or site title](https://full-url)`. Cite a source for every factual
claim — where practical, reference the source number(s) inline next to an item,
e.g. "(source 3)". Do not list a source you did not actually open.

If you genuinely cannot find notable events for a category, say so briefly rather
than inventing anything."""

_VERIFIER_INSTRUCTIONS = """\
You are an independent fact-checking editor. You did NOT write the draft below;
your job is to verify it before it reaches the reader. You have a web search
tool — USE IT to INDEPENDENTLY re-check every factual claim (dates, names,
places, scores, outcomes) against reputable sources. Do not trust the draft's
own sources blindly; find corroboration yourself.

For each claim, decide:
- VERIFIED — confirmed by a reliable source. Keep it.
- CORRECTED — the draft was wrong; fix it and note what changed.
- UNVERIFIED — you could not confirm it. Either remove it or clearly flag it as
  unconfirmed. Never let an unverified claim stand as if it were fact.

Then output, in Markdown, exactly this structure:

1. The corrected, final report (same categories and style as the draft, with any
   fixes applied and unconfirmed items flagged or removed).
2. A "## Verification Notes" section: a short bullet list summarising what you
   verified, what you corrected (old → new), and what you could not confirm.
3. A "## Sources" section: a clean, de-duplicated numbered list of Markdown links
   (`1. [Title](https://full-url)`) to the pages YOU used to verify, merged with
   any of the draft's sources you independently confirmed.

Keep the special attention to India and global coverage. Be rigorous and concise.
If the draft already looks fully correct, say so in the Verification Notes."""


@dataclass
class ResearchResult:
    """The outcome of a single agent run (researcher or verifier)."""

    markdown: str
    model: str
    used_web_search: bool


def build_prompt(parsed: ParsedDate, country: str | None = None) -> str:
    """Construct the researcher prompt for a parsed date."""
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


def build_verification_prompt(parsed: ParsedDate, draft_markdown: str) -> str:
    """Construct the verifier prompt wrapping the researcher's draft."""
    return (
        f"The date under research is {parsed.human()}"
        f"{' (this exact date)' if parsed.has_year else ' (any year)'}.\n\n"
        f"Below is a draft report to fact-check. Independently verify it with web "
        f"search, correct any errors, flag or remove anything you cannot confirm, "
        f"and produce the final report with Verification Notes and a consolidated "
        f"Sources list.\n\n--- DRAFT REPORT START ---\n{draft_markdown}\n"
        f"--- DRAFT REPORT END ---"
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


def _resolve_model(model: str | None) -> str:
    return model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL


def _run_agent(client, model: str, instructions: str, prompt: str) -> ResearchResult:
    """Run one Responses call with web search, with graceful fallbacks.

    Tries each known web-search tool name; if the tool itself is unsupported,
    falls back to a non-search call so the user still gets an answer (clearly
    flagged via ``used_web_search``).
    """
    last_error: Exception | None = None
    for tool_type in _WEB_SEARCH_TOOL_TYPES:
        try:
            response = client.responses.create(
                model=model,
                tools=[{"type": tool_type}],
                instructions=instructions,
                input=prompt,
            )
            return ResearchResult(response.output_text.strip(), model, True)
        except Exception as exc:  # noqa: BLE001 - inspect, then retry/fall back
            last_error = exc
            if _is_unsupported_tool_error(exc):
                continue  # try the next tool name
            break

    # Last resort: run without web search rather than fail outright.
    try:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=prompt
            + "\n\n(Note: web search is unavailable; work from your own "
            "knowledge and clearly state that results were not web-verified.)",
        )
        return ResearchResult(response.output_text.strip(), model, False)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"OpenAI request failed: {exc}") from (last_error or exc)


def research_date(
    parsed: ParsedDate,
    *,
    country: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    client=None,
) -> ResearchResult:
    """Run the researcher agent for a parsed date and return a Markdown draft.

    Args:
        parsed: The structured date to research.
        country: Optional country to emphasise.
        model: OpenAI model id. Falls back to OPENAI_MODEL then DEFAULT_MODEL.
        api_key: OpenAI API key. Falls back to the OPENAI_API_KEY env var.
        client: An existing OpenAI client to reuse (mainly for the pipeline/tests).

    Raises:
        RuntimeError: If the SDK/API key is missing or the API call fails.
    """
    client = client or _build_client(api_key)
    model = _resolve_model(model)
    prompt = build_prompt(parsed, country=country)
    return _run_agent(client, model, _RESEARCHER_INSTRUCTIONS, prompt)


def verify_report(
    parsed: ParsedDate,
    draft: ResearchResult,
    *,
    model: str | None = None,
    api_key: str | None = None,
    client=None,
) -> ResearchResult:
    """Run the independent verifier agent over a researcher's draft.

    Returns a corrected report that includes Verification Notes and a
    consolidated Sources section.
    """
    client = client or _build_client(api_key)
    model = _resolve_model(model)
    prompt = build_verification_prompt(parsed, draft.markdown)
    return _run_agent(client, model, _VERIFIER_INSTRUCTIONS, prompt)


def investigate(
    parsed: ParsedDate,
    *,
    country: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    verify: bool = True,
    on_stage=None,
) -> ResearchResult:
    """Run the full pipeline: research, then (optionally) independent verification.

    Args:
        parsed: The structured date to research.
        country: Optional country to emphasise.
        model: OpenAI model id.
        api_key: OpenAI API key.
        verify: When True (default), the verifier agent fact-checks the draft.
        on_stage: Optional callback ``on_stage(name)`` invoked with ``"research"``
            and ``"verify"`` so a CLI can report progress.

    Returns:
        The final :class:`ResearchResult` (verified when ``verify`` is True).
    """
    client = _build_client(api_key)
    model = _resolve_model(model)

    if on_stage:
        on_stage("research")
    draft = research_date(parsed, country=country, model=model, client=client)

    if not verify:
        return draft

    if on_stage:
        on_stage("verify")
    return verify_report(parsed, draft, model=model, client=client)


def _is_unsupported_tool_error(exc: Exception) -> bool:
    """Heuristic: does this error indicate the web search tool name is unknown?"""
    message = str(exc).lower()
    return "tool" in message and (
        "web_search" in message or "unsupported" in message or "unknown" in message
    )
