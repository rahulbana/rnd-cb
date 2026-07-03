"""Command line interface for the code review agent."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

from . import __version__
from .collector import CollectorError, collect
from .config import ConfigError, load_settings
from .formatter import render
from .models import FileReview
from .reviewer import ReviewEngine

logger = logging.getLogger("code_review_agent")

# Exit codes (useful for CI pipelines).
EXIT_OK = 0
EXIT_ISSUES_FOUND = 1
EXIT_CONFIG_ERROR = 2
EXIT_INPUT_ERROR = 3
EXIT_RUNTIME_ERROR = 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-review",
        description=(
            "LLM-powered code review agent. Reviews a single file or a "
            "directory for security, data-type, harmful-code and other "
            "quality concerns."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("path", help="File or directory to review.")
    parser.add_argument(
        "language",
        help="Programming language of the code (e.g. python, javascript, go).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["review", "json", "pretty"],
        default="review",
        help=(
            "Output format. 'review' = compact contract (default), "
            "'json' = full report with summary, 'pretty' = console view."
        ),
    )
    parser.add_argument(
        "-o", "--output", help="Write output to this file instead of stdout."
    )
    parser.add_argument(
        "-m", "--model", help="Override the OpenAI model (else OPENAI_MODEL / default)."
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        help="Number of files to review in parallel.",
    )
    parser.add_argument(
        "--env-file",
        help="Path to a .env file to load (defaults to auto-discovery).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colours in 'pretty' output.",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with code 1 if any issue is found (handy in CI).",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    # 1. Load configuration / credentials.
    try:
        settings = load_settings(
            args.env_file, model=args.model, concurrency=args.concurrency
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    # 2. Collect target files.
    try:
        targets = collect(
            args.path, args.language, max_file_bytes=settings.max_file_bytes
        )
    except CollectorError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    logger.info("Reviewing %d file(s) with model '%s'", len(targets), settings.model)

    # 3. Run the review.
    def _progress(review: FileReview) -> None:
        if args.verbose:
            status = "error" if review.error else f"{review.issue_count} issue(s)"
            logger.info("  reviewed %s -> %s", review.file, status)

    try:
        engine = ReviewEngine(settings)
        report = engine.review_files(
            targets, target_label=args.path, progress=_progress
        )
    except Exception as exc:  # noqa: BLE001 - top-level guard
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    # 4. Render + emit.
    color = (not args.no_color) and sys.stdout.isatty()
    rendered = render(report, args.format, color=color)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
        logger.info("Wrote report to %s", args.output)
    else:
        print(rendered)

    # 5. Exit code.
    if report.failed_files and report.failed_files == len(report.reviews):
        # Every file failed to review (e.g. auth/network) -> runtime error.
        return EXIT_RUNTIME_ERROR
    if args.fail_on_issues and report.total_issues > 0:
        return EXIT_ISSUES_FOUND
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
