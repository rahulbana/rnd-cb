"""Command-line interface for the festival-date agent.

Usage examples:
    festival Diwali 1984
    festival "Eid al-Fitr" 2025
    festival --question "When did we celebrate Holi in 1995?"
    festival                      # interactive mode
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .agent import FestivalAgent, FestivalResult

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional at runtime
    pass

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    _console: Optional["Console"] = Console()
except ImportError:  # fall back to plain printing if rich isn't installed
    _console = None


_CONFIDENCE_COLOR = {"high": "green", "medium": "yellow", "low": "red"}


def _render(result: FestivalResult) -> None:
    """Pretty-print a result, using rich when available."""
    if _console is None:
        _render_plain(result)
        return

    if not result.found:
        _console.print(
            Panel(
                Text(
                    f"Sorry — I couldn't pin down a date for "
                    f"'{result.festival}' in {result.year}.\n{result.notes}".strip(),
                    style="red",
                ),
                title="No date found",
                border_style="red",
            )
        )
        return

    body = Text()
    body.append(f"{result.festival} — {result.year}\n\n", style="bold cyan")
    body.append("Date:       ", style="bold")
    body.append(f"{result.date}", style="bold white")
    if result.day_of_week:
        body.append(f"  ({result.day_of_week})")
    body.append("\n")
    if result.date_range:
        body.append("Full span:  ", style="bold")
        body.append(f"{result.date_range}\n")
    color = _CONFIDENCE_COLOR.get(result.confidence, "white")
    body.append("Confidence: ", style="bold")
    body.append(f"{result.confidence}\n", style=color)
    if result.notes:
        body.append("\n")
        body.append(result.notes, style="italic dim")

    _console.print(Panel(body, title="🗓  Festival date", border_style="cyan"))


def _render_plain(result: FestivalResult) -> None:
    if not result.found:
        print(f"No date found for '{result.festival}' in {result.year}.")
        if result.notes:
            print(result.notes)
        return
    print(f"{result.festival} — {result.year}")
    line = f"Date: {result.date}"
    if result.day_of_week:
        line += f" ({result.day_of_week})"
    print(line)
    if result.date_range:
        print(f"Full span: {result.date_range}")
    print(f"Confidence: {result.confidence}")
    if result.notes:
        print(f"Note: {result.notes}")


def _interactive(agent: FestivalAgent) -> None:
    prompt = "Ask me a festival (e.g. 'Diwali 1984' or 'When was Eid in 2025?'). "
    print(prompt + "Type 'quit' to exit.\n")
    while True:
        try:
            query = input("festival> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            return
        try:
            _render(agent.ask(query))
        except Exception as exc:  # keep the loop alive on transient errors
            print(f"Error: {exc}")
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="festival",
        description="Ask an OpenAI-powered agent when a festival was celebrated.",
    )
    parser.add_argument(
        "festival",
        nargs="?",
        help="Festival name, e.g. 'Diwali' or 'Eid al-Fitr'.",
    )
    parser.add_argument(
        "year",
        nargs="?",
        type=int,
        help="The year to look up, e.g. 1984.",
    )
    parser.add_argument(
        "-q",
        "--question",
        help="Ask a free-form question instead of festival + year.",
    )
    parser.add_argument(
        "--model",
        help="Override the OpenAI model (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON result instead of a formatted panel.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        agent = FestivalAgent(model=args.model)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    # Decide what the user actually asked for.
    if args.question:
        result = agent.ask(args.question)
    elif args.festival and args.year is not None:
        result = agent.lookup(args.festival, args.year)
    elif args.festival and args.year is None:
        # Single positional like "Diwali 1984" passed as one quoted string, or a
        # bare festival name — hand the whole thing to the model to interpret.
        result = agent.ask(args.festival)
    else:
        _interactive(agent)
        return 0

    if args.json:
        print(json.dumps(result.__dict__, indent=2))
    else:
        _render(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
