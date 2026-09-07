"""Command-line entrypoint for the pipeline.

Examples
--------
Run the bundled sample end-to-end and write both JSON and an HTML dashboard::

    product-intel run --sample --json report.json --html dashboard.html

Analyze a real Amazon product. Live scrape (needs the ``scraping`` extra +
``playwright install chromium``)::

    product-intel run --url "https://www.amazon.com/dp/B0XXXXXXXX" --live --html out.html

...or, if Amazon blocks the headless browser, save the page from your browser
(right-click -> Save Page As -> "Web Page, Complete" / HTML) and parse it::

    product-intel run --html-file product.html --url "https://www.amazon.com/dp/B0XXXXXXXX" --html out.html

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


def _build_scraper(args):
    if args.sample:
        return FixtureScraper(payload=_load_sample_payload())
    if args.fixture:
        return FixtureScraper(payload=_load_fixture_payload(args.fixture))
    if args.html_file:
        # Parse a page you saved from your browser (no network, no anti-bot).
        from .scrapers.amazon import parse_amazon

        with open(args.html_file, "r", encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        return FixtureScraper(payload=parse_amazon(html, source_url=args.url or ""))
    if args.url and args.live:
        from .scrapers.amazon import AmazonScraper, is_amazon_url

        if not is_amazon_url(args.url):
            raise SystemExit(
                "error: live scraping currently supports Amazon URLs only. "
                "For other sites, save the page and use --html-file, or provide "
                "a --fixture JSON payload."
            )
        return AmazonScraper(
            max_reviews=args.max_reviews, headless=not args.no_headless
        )
    return None


def cmd_run(args) -> int:
    # Load .env early so hosted-LLM API keys are available before any client
    # is constructed. Shell environment variables take precedence.
    from pathlib import Path

    from .dotenv import load_dotenv

    loaded = load_dotenv(Path(args.env_file) if args.env_file else None)
    if loaded and not args.quiet:
        print(f"Loaded environment from {loaded}", file=sys.stderr)

    scraper = _build_scraper(args)
    if scraper is None:
        print(
            "error: provide an input source - one of:\n"
            "  --sample                      bundled demo product\n"
            "  --fixture PATH                a scraped-payload JSON file\n"
            "  --html-file PATH [--url URL]  an Amazon page saved from your browser\n"
            "  --url AMAZON_URL --live       scrape Amazon live (needs the scraping extra)",
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
    src.add_argument("--url", metavar="URL", default="", help="Amazon product detail URL.")
    src.add_argument("--live", action="store_true",
                     help="Scrape --url live via Playwright (Amazon only; needs the 'scraping' extra).")
    src.add_argument("--html-file", metavar="PATH",
                     help="Parse an Amazon product page saved from your browser (no network).")
    src.add_argument("--max-reviews", type=int, default=100, metavar="N",
                     help="Cap reviews fetched during live scraping (default: 100).")
    src.add_argument("--no-headless", action="store_true",
                     help="Show the browser window during live scraping (can dodge some blocks).")

    out = run.add_argument_group("output")
    out.add_argument("--json", metavar="PATH", help="Write the JSON report to PATH.")
    out.add_argument("--html", metavar="PATH", help="Write the HTML dashboard to PATH.")
    out.add_argument("--strict-schema", action="store_true",
                     help="Emit only the plan's core schema (omit diagnostics).")

    run.add_argument("--llm", choices=["offline", "anthropic", "openai"], default="offline",
                     help="Synthesis engine (default: offline, deterministic).")
    run.add_argument("--env-file", metavar="PATH", default=None,
                     help="Path to a .env file (default: auto-discover from the cwd upward).")
    run.add_argument("--quiet", "-q", action="store_true", help="Suppress progress logs.")
    run.set_defaults(func=cmd_run)
    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
