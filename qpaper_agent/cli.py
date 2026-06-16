"""Command-line interface for the question-paper agent system.

Examples
--------
    python -m qpaper_agent --board CBSE --class 10 --subject English
    python -m qpaper_agent --board "UP Board" --class 12 --subject Hindi \\
        --years 2022 2023 2024 --max 8
    python -m qpaper_agent --board ICSE --class 10 --subject Mathematics --dry-run
"""

from __future__ import annotations

import argparse
import sys

from .config import Settings
from .models import PaperRequest
from .orchestrator import Orchestrator


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qpaper_agent",
        description="Plan, find, validate and download board exam question "
        "papers (CBSE / ICSE / UP Board / ...) using an OpenAI multi-agent "
        "pipeline.",
    )
    p.add_argument("--board", required=True, help="Board, e.g. CBSE, ICSE, UP Board.")
    p.add_argument(
        "--class", dest="klass", required=True, help="Class/grade, e.g. 10 or 12."
    )
    p.add_argument("--subject", required=True, help="Subject, e.g. English, Hindi.")
    p.add_argument(
        "--paper-type",
        default="previous year question papers",
        help="Kind of papers (previous year, sample, model, ...).",
    )
    p.add_argument(
        "--years",
        nargs="*",
        type=int,
        default=[],
        help="Specific years to target. Omit for recent years.",
    )
    p.add_argument(
        "--max", dest="max_papers", type=int, default=10, help="Max papers to fetch."
    )
    p.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Validator confidence threshold for accepting a paper (0-1).",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Where to save papers (overrides QPAPER_OUTPUT_DIR).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Run planning/search/validation but do not download files.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    settings = Settings.from_env()
    if args.output_dir:
        # Settings is frozen; rebuild with the override.
        settings = Settings(
            openai_api_key=settings.openai_api_key,
            model=settings.model,
            search_model=settings.search_model,
            output_dir=args.output_dir,
            request_timeout=settings.request_timeout,
            max_candidates=settings.max_candidates,
        )

    try:
        settings.require_api_key()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    request = PaperRequest(
        board=args.board,
        subject=args.subject,
        klass=args.klass,
        paper_type=args.paper_type,
        years=args.years,
        max_papers=args.max_papers,
    )

    orchestrator = Orchestrator(
        settings,
        min_confidence=args.min_confidence,
        dry_run=args.dry_run,
    )
    report = orchestrator.run(request)
    downloaded = sum(1 for d in report.downloads if d.success)
    return 0 if downloaded or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
