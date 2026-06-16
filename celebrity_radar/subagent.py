"""A single specialized search sub-agent.

Each sub-agent is one web-search-equipped call to the OpenAI Responses API. OpenAI runs
the search loop server-side and returns a completed response; we extract the findings
text plus the sources (URL citations) it relied on.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

import openai

from .config import SearchAgentSpec, SUBAGENT_MODEL


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


def _supports_reasoning(model: str) -> bool:
    return model.startswith(("gpt-5", "o1", "o3", "o4"))


def _build_web_search_tool(spec: SearchAgentSpec) -> dict:
    tool: dict = {"type": "web_search"}
    if spec.allowed_domains:
        tool["filters"] = {"allowed_domains": spec.allowed_domains}
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


def _extract(response) -> tuple[str, list[Source]]:
    """Pull the final text and URL citations out of a completed Responses API result."""
    text = (getattr(response, "output_text", None) or "").strip()
    sources: dict[str, Source] = {}
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            for ann in getattr(content, "annotations", None) or []:
                if getattr(ann, "type", None) != "url_citation":
                    continue
                url = getattr(ann, "url", None)
                if not url:
                    continue
                title = getattr(ann, "title", None) or url
                sources.setdefault(url, Source(title=title, url=url))
    return text, list(sources.values())


async def run_search_agent(
    client: openai.AsyncOpenAI,
    celebrity: str,
    spec: SearchAgentSpec,
) -> AgentFindings:
    """Run one specialized sub-agent to completion and return its findings."""
    kwargs: dict = {
        "model": SUBAGENT_MODEL,
        "instructions": _system_prompt(celebrity, spec),
        "input": (
            f"Research \"{celebrity}\" within your focus area and report what you find."
        ),
        "tools": [_build_web_search_tool(spec)],
        "max_output_tokens": 8000,
    }
    if _supports_reasoning(SUBAGENT_MODEL):
        kwargs["reasoning"] = {"effort": "low"}

    try:
        response = await client.responses.create(**kwargs)
        findings, sources = _extract(response)
        if not findings:
            return AgentFindings(
                spec=spec,
                findings="",
                sources=sources,
                error="No findings returned (possible refusal or empty result).",
            )
        return AgentFindings(spec=spec, findings=findings, sources=sources)
    except openai.OpenAIError as exc:  # surface, don't crash the whole fan-out
        return AgentFindings(spec=spec, findings="", sources=[], error=str(exc))
