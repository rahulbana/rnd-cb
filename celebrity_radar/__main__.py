"""Command-line entry point: ``python -m celebrity_radar "<celebrity name>"``."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .orchestrator import CelebrityReport, research_celebrity


def _render(report: CelebrityReport) -> str:
    lines = [f"# Celebrity Radar — {report.celebrity}", "", report.report]

    if report.sources:
        lines += ["", "## Sources", ""]
        for i, s in enumerate(report.sources, 1):
            lines.append(f"{i}. [{s.title}]({s.url})")

    # Note any agents that failed so the gaps are visible.
    failed = [f for f in report.agent_findings if f.error]
    if failed:
        lines += ["", "## Agent notes", ""]
        for f in failed:
            lines.append(f"- {f.spec.title}: failed ({f.error})")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="celebrity_radar",
        description=(
            "Research recent news, incidents, and scams about a celebrity using "
            "multiple concurrent web-search agents."
        ),
    )
    parser.add_argument("celebrity", help="Name of the celebrity / public figure")
    parser.add_argument(
        "-o", "--output", help="Write the Markdown report to this file as well as stdout"
    )
    args = parser.parse_args(argv)

    try:
        report = asyncio.run(research_celebrity(args.celebrity))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130

    rendered = _render(report)
    print(rendered)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered + "\n")
        print(f"\n[saved to {args.output}]", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
