"""Local (non-MCP) tools exposed to the agent."""

from agentic_app.tools.currency import convert_currency
from agentic_app.tools.web_search import web_search_duckduckgo, web_search_tavily

# All local function-tools the agent should be given.
LOCAL_TOOLS = [web_search_tavily, web_search_duckduckgo, convert_currency]

__all__ = [
    "LOCAL_TOOLS",
    "web_search_tavily",
    "web_search_duckduckgo",
    "convert_currency",
]
