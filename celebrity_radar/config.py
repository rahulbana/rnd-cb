"""Configuration: models and the roster of specialized search sub-agents."""

from __future__ import annotations

from dataclasses import dataclass, field

# Default to a capable model that supports the Responses API web_search tool and
# reasoning effort. The synthesis step does the heavy reasoning (high effort); the
# search sub-agents run at low effort to stay cheap and fast since the web_search
# tool does most of their work.
ORCHESTRATOR_MODEL = "gpt-5"
SUBAGENT_MODEL = "gpt-5"


@dataclass(frozen=True)
class SearchAgentSpec:
    """Defines one specialized search sub-agent.

    Each sub-agent is an independent web-search-equipped model call with its own focus
    and (optionally) a curated set of domains to restrict the search to.
    """

    key: str
    """Short machine identifier, e.g. ``"scams"``."""

    title: str
    """Human-readable label shown in the report, e.g. ``"Scams & Impersonation"``."""

    focus: str
    """Instructions describing what this sub-agent should hunt for."""

    allowed_domains: list[str] = field(default_factory=list)
    """If non-empty, restrict web search to these domains (OpenAI web_search filters)."""


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
    ),
    SearchAgentSpec(
        key="incidents_legal",
        title="Incidents, Legal & Controversy",
        focus=(
            "Find incidents, accidents, arrests, lawsuits, legal disputes, public "
            "controversies, and statements/apologies. Capture the timeline and the "
            "current status of any ongoing matter."
        ),
    ),
    SearchAgentSpec(
        key="social_reaction",
        title="Social Media & Public Reaction",
        focus=(
            "Find what is being said on and about social media — viral posts, trends, "
            "fan and public reaction, and any misinformation or rumors circulating. "
            "Distinguish confirmed facts from unverified claims."
        ),
    ),
]
