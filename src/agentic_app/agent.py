"""Assembles the OpenAI-powered agent: LLM + local tools + remote MCP server."""

from __future__ import annotations

from agents import Agent, set_default_openai_key
from agents.mcp import MCPServerStreamableHttp

from agentic_app.config import get_settings
from agentic_app.tools import LOCAL_TOOLS


def configure_openai() -> None:
    """Register the OpenAI API key with the Agents SDK from settings.

    The SDK also reads OPENAI_API_KEY from the environment automatically, but
    setting it explicitly lets us source the key from our own config layer
    (.env / pydantic-settings) as the single source of truth. No-op if unset.
    """
    settings = get_settings()
    if settings.openai_api_key:
        # Correct import is `from agents import set_default_openai_key`
        # (there is no `agents.config` module in the SDK).
        set_default_openai_key(settings.openai_api_key)

INSTRUCTIONS = """\
You are a capable business assistant for a client-services team.

You have three families of tools:
1. Client directory (via MCP): create, look up, update, list, delete, and search
   client records (name, country, state, city, contact number, email). Use these
   whenever the user asks about clients or wants to store/retrieve contact info.
2. Web search: `web_search_tavily` (preferred when available) and
   `web_search_duckduckgo` (keyless fallback). Use for current events, facts, and
   research. If one engine returns an error, try the other.
3. Currency conversion: `convert_currency` for FX using live rates.

Guidelines:
- Prefer tools over guessing. For anything about a specific client, query the
  directory rather than relying on memory.
- When creating a client, `name`, `country`, `state`, and `email` are mandatory.
  If any is missing, ask the user for it before calling `add_client`. Confirm the
  key fields back to the user after creating or updating a client.
- Cite source URLs when you answer from web search.
- Be concise and factual. If a tool errors, explain briefly and adapt.
"""


def build_mcp_server() -> MCPServerStreamableHttp:
    """Create (but do not connect) the remote MCP client-directory server."""
    settings = get_settings()
    return MCPServerStreamableHttp(
        name="client-directory",
        params={"url": settings.mcp_server_url},
        # Cache the tool list for the session; the directory's tool set is static.
        cache_tools_list=True,
        client_session_timeout_seconds=30,
    )


def build_agent(mcp_server: MCPServerStreamableHttp) -> Agent:
    """Build the agent bound to the OpenAI model, local tools, and the MCP server."""
    configure_openai()
    settings = get_settings()
    return Agent(
        name="Client Services Assistant",
        instructions=INSTRUCTIONS,
        model=settings.openai_model,
        tools=list(LOCAL_TOOLS),
        mcp_servers=[mcp_server],
    )
