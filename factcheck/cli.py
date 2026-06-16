"""Command-line entry point for the fact-checking agent."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from .agent import FactCheckAgent
from .config import ConfigError, Settings
from .output import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="factcheck",
        description=(
            "Fact-check a statement strictly against live web sources. "
            "The LLM reasons ONLY over text gathered from the web — never its own memory."
        ),
    )
    parser.add_argument(
        "claim",
        nargs="?",
        help="The statement, news title, or claim to verify. Reads from stdin if omitted.",
    )
    parser.add_argument("--model", default=None, help="OpenAI model (default: env OPENAI_MODEL or gpt-4o).")
    parser.add_argument("--max-queries", type=int, default=4, help="Number of search queries to generate.")
    parser.add_argument("--results-per-query", type=int, default=5, help="Results requested per query.")
    parser.add_argument("--max-sources", type=int, default=12, help="Max sources passed to the verdict model.")
    parser.add_argument(
        "--depth",
        choices=["basic", "advanced"],
        default="advanced",
        help="Tavily search depth ('advanced' = deeper search).",
    )
    parser.add_argument("--json", action="store_true", help="Emit the full report as JSON instead of a table.")
    return parser


def _read_claim(arg_claim: str | None) -> str:
    if arg_claim and arg_claim.strip():
        return arg_claim.strip()
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            return piped
    raise SystemExit("Error: no claim provided. Pass it as an argument or via stdin.")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console()
    err = Console(stderr=True)

    claim = _read_claim(args.claim)

    try:
        settings = Settings.from_env(model=args.model)
    except ConfigError as exc:
        err.print(f"[bold red]Configuration error:[/bold red] {exc}")
        return 2

    progress = (lambda msg: None) if args.json else (lambda msg: err.print(f"[dim]{msg}[/dim]"))
    agent = FactCheckAgent(settings, progress=progress)

    try:
        report = agent.check(
            claim,
            max_queries=args.max_queries,
            results_per_query=args.results_per_query,
            max_sources=args.max_sources,
            depth=args.depth,
        )
    except Exception as exc:  # noqa: BLE001 - present a clean CLI error
        err.print(f"[bold red]Fact-check failed:[/bold red] {exc}")
        return 1

    if args.json:
        console.print_json(report.model_dump_json(indent=2))
    else:
        render_report(report, console)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
