"""Command-line entry point for cribasagent.

Examples
--------
Run once now and write the brief::

    python -m cribasagent run

Start the daily scheduler (default 10:00 local)::

    python -m cribasagent schedule
"""

from __future__ import annotations

import argparse
import logging
import sys

from .agent import CribasAgent
from .config import Config


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_dotenv() -> None:
    """Best-effort load of a local .env so API keys are picked up."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def build_parser() -> argparse.ArgumentParser:
    # Common options live on a parent parser so they're accepted both before
    # and after the subcommand (e.g. ``cribasagent run --model gpt-4o``).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    common.add_argument(
        "--lookback-hours", type=int, help="override the news lookback window"
    )
    common.add_argument("--model", help="override the OpenAI model")
    common.add_argument("--output-dir", help="override the output directory")

    parser = argparse.ArgumentParser(
        prog="cribasagent",
        description="Daily UPSC current-affairs agent (Indian English press → "
        "exam-ready Markdown brief).",
    )

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run", parents=[common], help="run a single cycle now (default)")
    sub.add_parser(
        "schedule", parents=[common], help="run every day at the configured time"
    )
    return parser


# Subcommands carry the flags; "run" is the default when none is given.
_COMMANDS = {"run", "schedule"}


def _normalise_argv(argv: list[str] | None) -> list[str]:
    """Default to the ``run`` subcommand so flags always have a home."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not any(tok in _COMMANDS for tok in argv):
        argv.insert(0, "run")
    return argv


def _config_from_args(args: argparse.Namespace) -> Config:
    config = Config()
    if args.lookback_hours is not None:
        config.lookback_hours = args.lookback_hours
    if args.model:
        config.model = args.model
    if args.output_dir:
        from pathlib import Path

        config.output_dir = Path(args.output_dir).expanduser()
    return config


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = build_parser().parse_args(_normalise_argv(argv))
    _configure_logging(args.verbose)
    config = _config_from_args(args)

    command = args.command or "run"
    try:
        if command == "schedule":
            from .scheduler import start

            start(config)
        else:
            path = CribasAgent(config).run()
            if path is None:
                return 1
            print(f"\n✅ Brief saved to: {path}")
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # surface a clean error to the shell
        logging.getLogger("cribasagent").error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
