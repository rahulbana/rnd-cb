"""LangGraph agent construction and tool wiring.

The agent's tools come from two places:

* **Remote MCP server** — the movie (TMDB) tools, discovered over
  streamable-HTTP via ``langchain-mcp-adapters``.
* **Native application tools** — translation and world-time helpers defined in
  :mod:`app.tools` and bundled directly into the backend.

Both sets are handed to a LangGraph ``create_react_agent`` powered by an OpenAI
chat model. The agent is built once at startup and reused across requests;
conversation state is supplied per request by the caller (the frontend sends
prior turns), so the graph itself is stateless and safe to share.
"""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from .config import Settings
from .tools import LOCAL_TOOLS

logger = logging.getLogger("backend.agent")


class Assistant:
    """Holds the compiled LangGraph agent and the MCP tools backing it."""

    def __init__(self, graph: CompiledStateGraph, tools: list[BaseTool], settings: Settings) -> None:
        self.graph = graph
        self.tools = tools
        self.settings = settings

    @property
    def tool_names(self) -> list[str]:
        return [tool.name for tool in self.tools]


async def build_assistant(settings: Settings) -> Assistant:
    """Connect to the MCP server, load tools, and compile the agent graph."""
    mcp_client = MultiServerMCPClient(
        {
            "tmdb-movies": {
                "url": settings.mcp_server_url,
                "transport": settings.mcp_transport,
            }
        }
    )

    logger.info("Loading movie tools from MCP server at %s", settings.mcp_server_url)
    mcp_tools = await mcp_client.get_tools()
    logger.info("Loaded %d MCP tools: %s", len(mcp_tools), [t.name for t in mcp_tools])

    # Movie tools (remote MCP) + translation/time tools (local application).
    tools = [*mcp_tools, *LOCAL_TOOLS]
    logger.info("Registered %d local tools: %s", len(LOCAL_TOOLS), [t.name for t in LOCAL_TOOLS])

    model = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        api_key=settings.openai_api_key,
        streaming=True,
    )

    graph = create_react_agent(model, tools, prompt=settings.system_prompt)
    return Assistant(graph=graph, tools=tools, settings=settings)
