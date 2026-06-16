"""Configuration: models and the roster of specialized search sub-agents."""

from __future__ import annotations

from dataclasses import dataclass, field

# Default to the most capable Opus model. The synthesis step does the heavy reasoning,
# so it runs at higher effort; the search sub-agents run at lower effort to stay cheap
# and fast since the web search tool does most of their work.
ORCHESTRATOR_MODEL = "claude-opus-4-8"
SUBAGENT_MODEL = "claude-opus-4-8"


@dataclass(frozen=True)
class SearchAgentSpec:
    """Defines one specialized search sub-agent.

    Each sub-agent is an independent web-search-equipped model call with its own focus
    and (optionally) a curated set of domains to prefer or avoid.
    """

    key: str
    """Short machine identifier, e.g. ``"scams"``."""

    title: str
    """Human-readable label shown in the report, e.g. ``"Scams & Impersonation"``."""

    focus: str
    """Instructions describing what this sub-agent should hunt for."""

    allowed_domains: list[str] = field(default_factory=list)
    """If non-empty, restrict web search to these domains."""

    blocked_domains: list[str] = field(default_factory=list)
    """Domains to exclude from web search (ignored if ``allowed_domains`` is set)."""

    max_searches: int = 6
    """Cap on web searches this sub-agent may run."""


# The default roster. Each agent targets a distinct angle so their findings complement
# rather than duplicate each other. Tune freely — add, remove, or re-scope agents.
DEFAULT_AGENTS: list[SearchAgentSpec] = [
    SearchAgentSpec(
        key="breaking_news",
        title="Recent News & Headlines",
        focus=(
            "Find the most recent news, headlines, and developments. Prioritize "
            "reputable mainstream outlets and entertainment news. Capture dates, what "
            "happened, and the outlet reporting it."
        ),
        max_searches=6,
    ),
    SearchAgentSpec(
        key="scams",
        title="Scams, Fraud & Impersonation",
        focus=(
            "Hunt specifically for scams that use this person's name, likeness, or "
            "voice: fake celebrity endorsements, crypto/investment schemes, deepfake "
            "videos, romance/impersonation scams, fraudulent giveaways, and phishing. "
            "Note whether the celebrity is the victim or is being impersonated, and "
            "include any official warnings or debunkings."
        ),
        max_searches=6,
    ),
    SearchAgentSpec(
        key="incidents_legal",
        title="Incidents, Legal & Controversy",
        focus=(
            "Find incidents, accidents, arrests, lawsuits, legal disputes, public "
            "controversies, and statements/apologies. Capture the timeline and the "
            "current status of any ongoing matter."
        ),
        max_searches=6,
    ),
    SearchAgentSpec(
        key="social_reaction",
        title="Social Media & Public Reaction",
        focus=(
            "Find what is being said on and about social media — viral posts, trends, "
            "fan and public reaction, and any misinformation or rumors circulating. "
            "Distinguish confirmed facts from unverified claims."
        ),
        max_searches=6,
    ),
]
