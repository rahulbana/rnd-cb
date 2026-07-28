"""Command-line entry point: run a research job to completion and print/export it.

Usage:
    research "Nvidia's data-center GPU moat" --depth deep --export report.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import get_settings
from app.jobs import JobManager
from app.models.schemas import JobStatus, ResearchDepth, ResearchRequest


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not settings.anthropic_api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2

    manager = JobManager(settings, run_factuality=not args.no_eval)
    request = ResearchRequest(
        topic=args.topic,
        audience=args.audience,
        depth=ResearchDepth(args.depth),
        focus_areas=[f.strip() for f in (args.focus or "").split(",") if f.strip()],
        max_iterations=args.max_iterations,
        max_usd_cost=args.max_cost,
    )
    record = manager.create_job(request)

    async for event in manager.subscribe(record.job_id):
        marker = {
            JobStatus.completed: "✓", JobStatus.failed: "✗",
            JobStatus.killed_budget: "⚑",
        }.get(event.status, "·")
        print(f"{marker} [{event.phase:>10}] {event.message}", file=sys.stderr)

    await record.task  # ensure completion

    if record.report is None:
        print(f"\nFailed: {record.error}", file=sys.stderr)
        return 1

    print(record.report.to_markdown())

    if record.factuality:
        print(f"\n<!-- Factuality: {record.factuality.score:.0%} "
              f"({record.factuality.supported} supported, "
              f"{record.factuality.contradicted} contradicted) -->")

    if args.export:
        from app.export import export_docx, export_pdf

        if args.export.endswith(".docx"):
            export_docx(record.report, args.export)
        else:
            export_pdf(record.report, args.export)
        print(f"\nExported to {args.export}", file=sys.stderr)

    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Deep Research Agent — CLI")
    p.add_argument("topic", help="Research topic")
    p.add_argument("--audience", default="a consulting firm's client")
    p.add_argument("--depth", default="standard", choices=[d.value for d in ResearchDepth])
    p.add_argument("--focus", default="", help="Comma-separated focus areas")
    p.add_argument("--max-iterations", type=int, default=None, dest="max_iterations")
    p.add_argument("--max-cost", type=float, default=None, dest="max_cost")
    p.add_argument("--export", default=None, help="Write report to a .pdf or .docx file")
    p.add_argument("--no-eval", action="store_true", help="Skip factuality evaluation")
    args = p.parse_args()

    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
