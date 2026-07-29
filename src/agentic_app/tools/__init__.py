"""Local (non-MCP) tools exposed to the agent, grouped by category."""

from agentic_app.tools.currency import convert_currency
from agentic_app.tools.web_search import web_search_duckduckgo, web_search_tavily

# Grouped so usage-tracking can label each call by category.
WEB_SEARCH_TOOLS = [web_search_tavily, web_search_duckduckgo]
CUSTOM_TOOLS = [convert_currency]

# All local function-tools the agent should be given.
LOCAL_TOOLS = [*WEB_SEARCH_TOOLS, *CUSTOM_TOOLS]

WEB_SEARCH_TOOL_NAMES = {t.name for t in WEB_SEARCH_TOOLS}
CUSTOM_TOOL_NAMES = {t.name for t in CUSTOM_TOOLS}

__all__ = [
    "LOCAL_TOOLS",
    "WEB_SEARCH_TOOLS",
    "CUSTOM_TOOLS",
    "WEB_SEARCH_TOOL_NAMES",
    "CUSTOM_TOOL_NAMES",
    "web_search_tavily",
    "web_search_duckduckgo",
    "convert_currency",
]
