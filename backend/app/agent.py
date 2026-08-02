"""LangGraph agent construction and MCP tool wiring.

The backend connects to the *remote* MCP server over streamable-HTTP, loads its
tools through ``langchain-mcp-adapters``, and hands them to a LangGraph
``create_react_agent`` powered by an OpenAI chat model. The agent is built once
at startup and reused across requests; conversation state is supplied per
request by the caller (the frontend sends prior turns), so the graph itself is
stateless and safe to share.
"""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from .config import Settings

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
            "movies-and-utilities": {
                "url": settings.mcp_server_url,
                "transport": settings.mcp_transport,
            }
        }
    )

    logger.info("Loading tools from MCP server at %s", settings.mcp_server_url)
    tools = await mcp_client.get_tools()
    logger.info("Loaded %d MCP tools: %s", len(tools), [t.name for t in tools])

    model = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        api_key=settings.openai_api_key,
        streaming=True,
    )

    graph = create_react_agent(model, tools, prompt=settings.system_prompt)
    return Assistant(graph=graph, tools=tools, settings=settings)
