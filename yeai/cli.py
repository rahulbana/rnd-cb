"""Command-line interface for the Ye'ai Assistant.

Run an interactive chat session, or ask a single question with ``-q``::

    python -m yeai                      # interactive REPL
    python -m yeai -q "Convert 50 USD to GBP"
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    _console: Any = Console()
    _RICH = True
except Exception:  # pragma: no cover - rich is optional.
    _console = None
    _RICH = False

from . import __version__
from .agent import AgentError, YeaiAgent

BANNER = "Ye'ai Assistant"
HELP_TEXT = (
    "Commands: type your question and press Enter. "
    "Use /tools to list tools, /reset to clear history, /exit (or Ctrl-D) to quit."
)


def _print(text: str) -> None:
    if _RICH:
        _console.print(text)
    else:
        print(text)


def _print_answer(text: str) -> None:
    if _RICH:
        _console.print(Panel(Markdown(text or "*(no answer)*"), title="Ye'ai", border_style="cyan"))
    else:
        print(f"\nYe'ai: {text}\n")


def _on_tool_call(name: str, args: Dict[str, Any]) -> None:
    rendered = ", ".join(f"{k}={v!r}" for k, v in args.items())
    msg = f"  [tool] {name}({rendered})"
    if _RICH:
        _console.print(f"[dim]{msg}[/dim]")
    else:
        print(msg)


def _interactive(agent: YeaiAgent) -> int:
    if _RICH:
        _console.print(Panel.fit(f"[bold cyan]{BANNER}[/bold cyan]  v{__version__}\n{HELP_TEXT}", border_style="cyan"))
    else:
        print(f"{BANNER} v{__version__}\n{HELP_TEXT}\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return 0

        if not user_input:
            continue
        lowered = user_input.lower()
        if lowered in ("/exit", "/quit", "exit", "quit"):
            print("Goodbye!")
            return 0
        if lowered == "/reset":
            agent.reset()
            _print("History cleared.")
            continue
        if lowered == "/tools":
            _print("Available tools: " + ", ".join(agent.tool_names))
            continue
        if lowered in ("/help", "help"):
            _print(HELP_TEXT)
            continue

        try:
            answer = agent.ask(user_input, on_tool_call=_on_tool_call)
        except Exception as exc:  # noqa: BLE001 - keep the REPL alive.
            _print(f"[error] {exc}")
            continue
        _print_answer(answer)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yeai",
        description="Ye'ai Assistant -- a CLI AI agent powered by OpenAI.",
    )
    parser.add_argument(
        "-q",
        "--question",
        help="Ask a single question and print the answer (non-interactive).",
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Override the OpenAI model to use for this run.",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List the available tools and exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_tools:
        from .tools.base import build_registry

        for name, tool in build_registry().items():
            _print(f"- {name}: {tool.description}")
        return 0

    try:
        agent = YeaiAgent(model=args.model)
    except AgentError as exc:
        _print(f"[error] {exc}")
        return 1

    if args.question:
        try:
            answer = agent.ask(args.question, on_tool_call=_on_tool_call)
        except Exception as exc:  # noqa: BLE001
            _print(f"[error] {exc}")
            return 1
        _print_answer(answer)
        return 0

    return _interactive(agent)


if __name__ == "__main__":
    sys.exit(main())
