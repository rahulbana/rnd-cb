"""CLI entrypoint: an interactive, multi-turn chat loop over the agent.

Usage:
    python -m agentic_app.main                 # interactive REPL
    python -m agentic_app.main "one-off query" # single-shot query and exit

Requires the MCP server to be running (see README) and OPENAI_API_KEY set.
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter

from agents import Runner
from agents.exceptions import AgentsException
from rich.console import Console
from rich.markdown import Markdown

from agentic_app.agent import build_agent, build_mcp_server
from agentic_app.config import get_settings
from agentic_app.observability import configure_langfuse, flush_langfuse
from agentic_app.tools import CUSTOM_TOOL_NAMES, WEB_SEARCH_TOOL_NAMES
from agentic_app.tracking import ToolUsageTracker

console = Console()


async def _mcp_tool_names(mcp_server) -> set[str]:
    """Names of the tools the connected MCP server exposes (for categorization)."""
    try:
        return {t.name for t in await mcp_server.list_tools()}
    except Exception:  # noqa: BLE001 - tracking is best-effort, never block the run
        return set()


def _new_tracker(mcp_names: set[str]) -> ToolUsageTracker:
    return ToolUsageTracker(
        mcp_tool_names=mcp_names,
        web_tool_names=WEB_SEARCH_TOOL_NAMES,
        custom_tool_names=CUSTOM_TOOL_NAMES,
    )


async def _run_once(query: str) -> None:
    async with build_mcp_server() as mcp_server:
        agent = build_agent(mcp_server)
        tracker = _new_tracker(await _mcp_tool_names(mcp_server))
        result = await Runner.run(agent, query, hooks=tracker)
        console.print(Markdown(str(result.final_output)))
        tracker.print_summary()


async def _repl() -> None:
    settings = get_settings()
    console.print(
        f"[bold green]Client Services Assistant[/] "
        f"(model: {settings.openai_model}, mcp: {settings.mcp_server_url})"
    )
    console.print("[dim]Type your message. Commands: /exit, /reset[/]\n")

    async with build_mcp_server() as mcp_server:
        agent = build_agent(mcp_server)
        mcp_names = await _mcp_tool_names(mcp_server)
        session_counts: Counter = Counter()
        history: list = []
        while True:
            try:
                user = console.input("[bold cyan]you ›[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]bye[/]")
                return
            if not user:
                continue
            if user in {"/exit", "/quit"}:
                console.print("[dim]bye[/]")
                return
            if user == "/reset":
                history = []
                console.print("[dim]conversation reset[/]\n")
                continue

            tracker = _new_tracker(mcp_names)
            try:
                result = await Runner.run(
                    agent,
                    history + [{"role": "user", "content": user}],
                    hooks=tracker,
                )
            except AgentsException as exc:
                console.print(f"[red]agent error:[/] {exc}")
                continue

            console.print("[bold magenta]assistant ›[/]")
            console.print(Markdown(str(result.final_output)))
            tracker.print_summary()
            session_counts.update(tracker.counts())
            if sum(session_counts.values()):
                totals = ", ".join(f"{k}×{v}" for k, v in session_counts.items())
                console.print(f"  [dim]session totals → {totals}[/]")
            console.print()
            # Carry full context forward for a coherent multi-turn conversation.
            history = result.to_input_list()


def _preflight() -> bool:
    settings = get_settings()
    if not settings.openai_api_key:
        console.print(
            "[red]OPENAI_API_KEY is not set.[/] Copy .env.example to .env and add your key."
        )
        return False
    return True


def cli() -> None:
    """Console-script entrypoint."""
    if not _preflight():
        sys.exit(1)
    configure_langfuse()  # no-op unless Langfuse keys are configured
    query = " ".join(sys.argv[1:]).strip()
    try:
        if query:
            asyncio.run(_run_once(query))
        else:
            asyncio.run(_repl())
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure buffered traces are sent before the process exits.
        flush_langfuse()


if __name__ == "__main__":
    cli()
