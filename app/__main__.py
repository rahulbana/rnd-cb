"""Interactive CLI (REPL) for the ecommerce assistant.

Run with:  python -m app

Slash commands:
    /reset   clear the conversation history
    /tools   list the available tools
    /help    show help
    /exit    quit  (also: Ctrl-D / Ctrl-C)
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .agent import Agent
from .config import Config
from .llm import LLMClient
from .tools import build_registry

console = Console()

BANNER = """[bold cyan]Ecommerce AI Assistant[/bold cyan]
Custom OpenAI function-calling agent — no orchestration framework.
Type your question, or [bold]/help[/bold] for commands. [bold]/exit[/bold] to quit."""


def _print_tool_call(name: str, args: dict) -> None:
    rendered = ", ".join(f"{k}={v!r}" for k, v in args.items())
    if len(rendered) > 160:
        rendered = rendered[:160] + "…"
    console.print(f"  [dim]→ {name}({rendered})[/dim]")


def _startup_checks(config: Config) -> None:
    if not config.openai_api_key:
        console.print("[bold red]OPENAI_API_KEY is not set.[/bold red] "
                      "Copy .env.example to .env and add your key.")
        sys.exit(1)
    from pathlib import Path

    if not Path(config.db_path).exists():
        console.print(
            f"[yellow]Note:[/yellow] database '{config.db_path}' not found. "
            "Run [bold]python scripts/init_db.py[/bold] to create and seed it."
        )
    if not config.tavily_api_key:
        console.print(
            "[yellow]Note:[/yellow] TAVILY_API_KEY not set — web search tools "
            "will report that they're unconfigured."
        )


def main() -> None:
    config = Config.from_env()
    _startup_checks(config)

    registry = build_registry(config)
    agent = Agent(LLMClient(config), registry, max_steps=config.max_steps)

    console.print(Panel(BANNER, expand=False, border_style="cyan"))
    console.print(f"[dim]Model: {config.openai_model} · Tools: "
                  f"{', '.join(registry.names())}[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]you ›[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/dim]")
            break

        if not user_input:
            continue

        low = user_input.lower()
        if low in {"/exit", "/quit", ":q"}:
            console.print("[dim]bye[/dim]")
            break
        if low == "/reset":
            agent.reset()
            console.print("[dim]conversation cleared[/dim]\n")
            continue
        if low == "/tools":
            console.print("[bold]Available tools:[/bold] " + ", ".join(registry.names()) + "\n")
            continue
        if low == "/help":
            console.print(Markdown(
                "**Commands:** `/reset` clear history · `/tools` list tools · "
                "`/exit` quit\n\nJust type a question to chat with the agent."
            ))
            continue

        try:
            with console.status("[dim]thinking…[/dim]", spinner="dots"):
                answer = agent.send(user_input, on_tool_call=_print_tool_call)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]Error:[/bold red] {exc}\n")
            continue

        console.print()
        console.print(Markdown(answer or "(no response)"))
        console.print()


if __name__ == "__main__":
    main()
