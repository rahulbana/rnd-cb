"""Orchestration: fan out to the search sub-agents concurrently, then synthesize."""

from __future__ import annotations

import asyncio
import datetime as _dt
from dataclasses import dataclass, field

import openai

from .config import SearchAgentSpec, DEFAULT_AGENTS, ORCHESTRATOR_MODEL
from .subagent import AgentFindings, Source, run_search_agent, _supports_reasoning


@dataclass
class CelebrityReport:
    """The final synthesized report plus the raw per-agent findings behind it."""

    celebrity: str
    report: str
    agent_findings: list[AgentFindings] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)


def _synthesis_system_prompt(celebrity: str) -> str:
    today = _dt.date.today().isoformat()
    return (
        f"You are an editor synthesizing research from several specialist agents into a "
        f"single briefing about the public figure \"{celebrity}\". Today is {today}.\n\n"
        "You will receive each agent's raw findings. Produce a clear, well-organized "
        "Markdown report with these sections (omit a section only if there is genuinely "
        "nothing credible to report for it):\n"
        "1. **Summary** — 2-4 sentences on the overall current picture.\n"
        "2. **Recent News** — notable recent developments with dates.\n"
        "3. **Scams & Impersonation** — any fraud using their name/likeness, with whether "
        "they are victim or impersonated, and any official warnings.\n"
        "4. **Incidents, Legal & Controversy** — incidents, lawsuits, disputes, status.\n"
        "5. **Social Media & Rumors** — public reaction; clearly separate confirmed facts "
        "from unverified rumors.\n\n"
        "Rules: Do not invent facts beyond the agents' findings. Flag conflicting reports. "
        "Mark anything unverified explicitly. Be concise and skimmable. Do not fabricate "
        "URLs — a consolidated source list is appended separately."
    )


def _format_agent_findings(findings: list[AgentFindings]) -> str:
    blocks: list[str] = []
    for f in findings:
        header = f"### Agent: {f.spec.title}"
        if f.error:
            blocks.append(f"{header}\n(failed: {f.error})")
        elif not f.findings:
            blocks.append(f"{header}\n(no findings)")
        else:
            blocks.append(f"{header}\n{f.findings}")
    return "\n\n".join(blocks)


def _consolidate_sources(findings: list[AgentFindings]) -> list[Source]:
    seen: dict[str, Source] = {}
    for f in findings:
        for s in f.sources:
            seen.setdefault(s.url, s)
    return list(seen.values())


async def _synthesize(
    client: openai.AsyncOpenAI,
    celebrity: str,
    findings: list[AgentFindings],
) -> str:
    user_content = (
        f"Here are the findings from the specialist agents researching \"{celebrity}\". "
        "Synthesize them into the briefing described in your instructions.\n\n"
        f"{_format_agent_findings(findings)}"
    )

    kwargs: dict = {
        "model": ORCHESTRATOR_MODEL,
        "instructions": _synthesis_system_prompt(celebrity),
        "input": user_content,
        "max_output_tokens": 16000,
    }
    if _supports_reasoning(ORCHESTRATOR_MODEL):
        kwargs["reasoning"] = {"effort": "high"}

    response = await client.responses.create(**kwargs)
    return (getattr(response, "output_text", None) or "").strip()


async def research_celebrity(
    celebrity: str,
    *,
    agents: list[SearchAgentSpec] | None = None,
    client: openai.AsyncOpenAI | None = None,
) -> CelebrityReport:
    """Research ``celebrity`` with the multi-agent pipeline and return a report.

    The search sub-agents run concurrently; their findings are then synthesized into a
    single Markdown briefing with a consolidated source list.
    """
    agents = agents or DEFAULT_AGENTS
    own_client = client is None
    client = client or openai.AsyncOpenAI()

    try:
        findings = await asyncio.gather(
            *(run_search_agent(client, celebrity, spec) for spec in agents)
        )
        findings = list(findings)
        report = await _synthesize(client, celebrity, findings)
    finally:
        if own_client:
            await client.close()

    return CelebrityReport(
        celebrity=celebrity,
        report=report,
        agent_findings=findings,
        sources=_consolidate_sources(findings),
    )
