"""A single specialized search sub-agent.

Each sub-agent is one web-search-equipped model call. Anthropic runs the search loop
server-side; we drive the conversation forward across ``pause_turn`` boundaries and then
extract the findings text plus the sources (citations) it relied on.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

import anthropic

from .config import SearchAgentSpec, SUBAGENT_MODEL

# Server-side web search tool with dynamic filtering (supported on Opus 4.x).
_WEB_SEARCH_TOOL_TYPE = "web_search_20260209"

# Cap on how many times we re-send to continue a server-side tool loop (pause_turn).
_MAX_CONTINUATIONS = 5


@dataclass
class Source:
    """A cited source surfaced by a sub-agent."""

    title: str
    url: str

    def __hash__(self) -> int:  # dedupe by URL
        return hash(self.url)


@dataclass
class AgentFindings:
    """The result of one sub-agent's research pass."""

    spec: SearchAgentSpec
    findings: str
    sources: list[Source]
    error: str | None = None


def _build_web_search_tool(spec: SearchAgentSpec) -> dict:
    tool: dict = {
        "type": _WEB_SEARCH_TOOL_TYPE,
        "name": "web_search",
        "max_uses": spec.max_searches,
    }
    if spec.allowed_domains:
        tool["allowed_domains"] = spec.allowed_domains
    elif spec.blocked_domains:
        tool["blocked_domains"] = spec.blocked_domains
    return tool


def _system_prompt(celebrity: str, spec: SearchAgentSpec) -> str:
    today = _dt.date.today().isoformat()
    return (
        f"You are a meticulous research agent. Today's date is {today}.\n"
        f"Your assignment: research the public figure \"{celebrity}\".\n\n"
        f"Your specific focus area — {spec.title}:\n{spec.focus}\n\n"
        "Rules:\n"
        "- Use the web_search tool to find current, recent information. Prefer the last "
        "12 months unless older context is essential.\n"
        "- Stay strictly within your focus area; another agent covers other angles.\n"
        "- Ground every claim in a search result. If you find nothing credible, say so "
        "plainly rather than speculating.\n"
        "- Be careful to attribute rumors and unverified claims as such.\n\n"
        "When done, write a concise briefing of your findings as bullet points. For each "
        "item include: what happened, the date if known, and the source. Do not write a "
        "preamble — output only the briefing."
    )


def _extract(message: anthropic.types.Message) -> tuple[str, list[Source]]:
    """Pull the final text and citation sources out of a completed message."""
    text_parts: list[str] = []
    sources: dict[str, Source] = {}
    for block in message.content:
        if block.type != "text":
            continue
        text_parts.append(block.text)
        for citation in getattr(block, "citations", None) or []:
            url = getattr(citation, "url", None)
            if not url:
                continue
            title = getattr(citation, "title", None) or url
            sources.setdefault(url, Source(title=title, url=url))
    return "\n".join(text_parts).strip(), list(sources.values())


async def run_search_agent(
    client: anthropic.AsyncAnthropic,
    celebrity: str,
    spec: SearchAgentSpec,
) -> AgentFindings:
    """Run one specialized sub-agent to completion and return its findings."""
    tools = [_build_web_search_tool(spec)]
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Research \"{celebrity}\" within your focus area and report what you find."
            ),
        }
    ]

    try:
        response = await client.messages.create(
            model=SUBAGENT_MODEL,
            max_tokens=8000,
            system=_system_prompt(celebrity, spec),
            tools=tools,
            output_config={"effort": "low"},
            messages=messages,
        )

        # The web search tool runs a server-side loop; it may pause and need to resume.
        continuations = 0
        while response.stop_reason == "pause_turn" and continuations < _MAX_CONTINUATIONS:
            messages.append({"role": "assistant", "content": response.content})
            response = await client.messages.create(
                model=SUBAGENT_MODEL,
                max_tokens=8000,
                system=_system_prompt(celebrity, spec),
                tools=tools,
                output_config={"effort": "low"},
                messages=messages,
            )
            continuations += 1

        if response.stop_reason == "refusal":
            return AgentFindings(
                spec=spec,
                findings="",
                sources=[],
                error="The model declined to research this request.",
            )

        findings, sources = _extract(response)
        return AgentFindings(spec=spec, findings=findings, sources=sources)

    except anthropic.APIError as exc:  # surface, don't crash the whole fan-out
        return AgentFindings(spec=spec, findings="", sources=[], error=str(exc))
