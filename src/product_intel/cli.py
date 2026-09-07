"""Command-line entrypoint for the pipeline.

Examples
--------
Run the bundled sample end-to-end and write both JSON and an HTML dashboard::

    product-intel run --sample --json report.json --html dashboard.html

Run against a scraped-payload fixture::

    product-intel run --fixture my_product.json --html out.html

Use a hosted LLM for synthesis (requires the matching extra + API key)::

    product-intel run --sample --llm anthropic   # Claude  (ANTHROPIC_API_KEY)
    product-intel run --sample --llm openai       # OpenAI  (OPENAI_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from importlib import resources
from typing import Optional

from .agents.web_ingestion import FixtureScraper
from .dashboard import render_dashboard
from .orchestrator import Orchestrator

SAMPLE_FIXTURE = "acousticpro_headphones.json"


def _load_sample_payload() -> dict:
    # Resolve through the top-level package (which always has a real origin);
    # chained joinpath keeps this working on Python 3.9, where Traversable
    # .joinpath accepts only a single path segment.
    resource = (
        resources.files("product_intel").joinpath("fixtures").joinpath(SAMPLE_FIXTURE)
    )
    with resource.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_fixture_payload(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _build_scraper(args) -> Optional[FixtureScraper]:
    if args.sample:
        return FixtureScraper(payload=_load_sample_payload())
    if args.fixture:
        return FixtureScraper(payload=_load_fixture_payload(args.fixture))
    if args.url and args.live:
        from .agents.web_ingestion import PlaywrightScraper

        return PlaywrightScraper()
    return None


def cmd_run(args) -> int:
    scraper = _build_scraper(args)
    if scraper is None:
        print(
            "error: provide one of --sample, --fixture PATH, or --url URL --live",
            file=sys.stderr,
        )
        return 2

    def progress(msg: str) -> None:
        if not args.quiet:
            print(msg, file=sys.stderr)

    orch = Orchestrator(
        scraper=scraper, llm_provider=args.llm, progress=progress
    )
    report = orch.run(url=args.url or "")
    payload = report.to_dict(include_diagnostics=not args.strict_schema)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        progress(f"Wrote JSON report -> {args.json}")

    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(render_dashboard(report))
        progress(f"Wrote HTML dashboard -> {args.html}")

    if not args.json and not args.html:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="product-intel",
        description="Multi-agent product review -> prioritized vNext backlog.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the full pipeline.")
    src = run.add_argument_group("input source")
    src.add_argument("--sample", action="store_true", help="Use the bundled sample product.")
    src.add_argument("--fixture", metavar="PATH", help="Path to a scraped-payload JSON file.")
    src.add_argument("--url", metavar="URL", default="", help="Product detail URL.")
    src.add_argument("--live", action="store_true",
                     help="Scrape --url live via Playwright (needs the 'scraping' extra).")

    out = run.add_argument_group("output")
    out.add_argument("--json", metavar="PATH", help="Write the JSON report to PATH.")
    out.add_argument("--html", metavar="PATH", help="Write the HTML dashboard to PATH.")
    out.add_argument("--strict-schema", action="store_true",
                     help="Emit only the plan's core schema (omit diagnostics).")

    run.add_argument("--llm", choices=["offline", "anthropic", "openai"], default="offline",
                     help="Synthesis engine (default: offline, deterministic).")
    run.add_argument("--quiet", "-q", action="store_true", help="Suppress progress logs.")
    run.set_defaults(func=cmd_run)
    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
