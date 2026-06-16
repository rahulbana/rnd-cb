"""Celebrity Radar — a multi-agent web researcher for news, incidents, and scams about a celebrity.

An orchestrator fans out to several specialized search sub-agents (each focused on a
different angle and source set) that run concurrently against OpenAI's Responses API
web_search tool, then a synthesis agent merges their cited findings into one report.
"""

from .config import SearchAgentSpec, DEFAULT_AGENTS, ORCHESTRATOR_MODEL, SUBAGENT_MODEL
from .orchestrator import research_celebrity, CelebrityReport

__all__ = [
    "SearchAgentSpec",
    "DEFAULT_AGENTS",
    "ORCHESTRATOR_MODEL",
    "SUBAGENT_MODEL",
    "research_celebrity",
    "CelebrityReport",
]
