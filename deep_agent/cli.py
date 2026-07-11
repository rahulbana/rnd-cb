"""Command-line interface for Deep Agent.

Examples::

    deep-agent doctor
    deep-agent research "Impact of GLP-1 drugs on healthcare costs"
    deep-agent research "Quantum error correction 2024" --iterations 2
    deep-agent config
"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from deep_agent.config import get_settings
from deep_agent.graph import run_research, save_report
from deep_agent.models.schemas import ReportStatus
from deep_agent.preflight import preflight_ok, run_preflight
from deep_agent.utils.logging import get_logger, setup_logging

app = typer.Typer(
    add_completion=False,
    help="Deep Agent — a multi-agent deep-research CLI.",
    no_args_is_help=True,
)
console = Console()
logger = get_logger("cli")


@app.command()
def research(
    topic: str = typer.Argument(..., help="The research topic / question."),
    iterations: int = typer.Option(
        None,
        "--iterations",
        "-n",
        help="Max research loop iterations (overrides config).",
    ),
    output_dir: str = typer.Option(
        None, "--output", "-o", help="Directory to write the markdown report."
    ),
    thread_id: str = typer.Option(
        None,
        "--thread-id",
        "-t",
        help="Checkpoint thread id (defaults to a slug of the topic).",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Show live per-node progress (stream) or run silently (invoke).",
    ),
    skip_preflight: bool = typer.Option(
        False, "--skip-preflight", help="Skip pre-run configuration checks."
    ),
) -> None:
    """Run the full research pipeline and save a markdown report."""

    setup_logging()
    console.print(
        Panel.fit(f"[bold cyan]Deep research[/]: {topic}", border_style="cyan")
    )

    if not skip_preflight:
        results = run_preflight()
        if not preflight_ok(results):
            failed = [r for r in results if r.critical and not r.ok]
            details = "\n".join(f"• {r.name}: {r.detail}" for r in failed)
            console.print(
                Panel.fit(
                    f"[bold red]Preflight failed[/] — fix these first:\n{details}\n\n"
                    "(Re-run with --skip-preflight to bypass.)",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1)

    # Human-friendly labels for the live progress line.
    node_labels = {
        "planner": "Planning research",
        "search": "Searching the web",
        "collector": "Collecting sources",
        "scraper": "Scraping pages",
        "reflection": "Reflecting on coverage",
        "fact_checker": "Fact-checking claims",
        "writer": "Writing report",
        "no_results": "No results",
    }

    def _on_node(node: str) -> None:
        console.print(f"  [green]✓[/] {node_labels.get(node, node)}")

    try:
        report = run_research(
            topic,
            max_iterations=iterations,
            thread_id=thread_id,
            stream=stream,
            on_node=_on_node if stream else None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Research failed")
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)

    path = save_report(report, output_dir=output_dir)

    if report.status is ReportStatus.NO_RESULTS:
        console.print(
            Panel.fit(
                f"[bold yellow]No report generated[/] — see {path}\n"
                "The pipeline could not gather enough evidence for this topic.",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=2)

    console.print(
        Panel.fit(
            f"[bold green]Report written[/] → {path}\n"
            f"Sources cited: {len(report.citations)}",
            border_style="green",
        )
    )


@app.command()
def doctor() -> None:
    """Validate configuration (API keys, broker, checkpointer) before a run."""

    setup_logging()
    results = run_preflight()
    table = Table(title="Deep Agent preflight", show_header=True)
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail", style="white")
    for r in results:
        if r.ok:
            status = "[green]OK[/]"
        else:
            status = "[red]FAIL[/]" if r.critical else "[yellow]WARN[/]"
        table.add_row(r.name, status, r.detail)
    console.print(table)

    if preflight_ok(results):
        console.print("[bold green]All critical checks passed.[/]")
    else:
        console.print("[bold red]Critical checks failed — fix before running.[/]")
        raise typer.Exit(code=1)


@app.command()
def config() -> None:
    """Show the active (resolved) configuration."""

    setup_logging()
    s = get_settings()
    table = Table(title="Deep Agent configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    rows = {
        "LLM provider": s.llm_provider.value,
        "LLM model": s.llm_model,
        "LLM fast model": s.llm_fast_model or "(same as model)",
        "LLM agent overrides": str(s.llm_agent_models or "(none)"),
        "LLM max tokens": str(s.llm_max_tokens or "(unset)"),
        "LLM cache": f"{s.llm_cache_backend.value}",
        "Context budget (chars)": str(s.max_context_chars),
        "Search provider": s.search_provider.value,
        "Search max results": str(s.search_max_results),
        "Max iterations": str(s.max_research_iterations),
        "Scrape concurrency": str(s.scrape_max_concurrency),
        "Respect robots.txt": str(s.respect_robots),
        "Scrape delay (s)": str(s.scrape_delay_seconds),
        "Stream progress": str(s.stream_progress),
        "Celery eager": str(s.celery_task_always_eager),
        "Celery broker": s.celery_broker_url,
        "Checkpoint backend": s.checkpoint_backend.value,
        "Checkpoint db": s.checkpoint_db,
        "Langfuse tracing": str(s.langfuse_enabled),
        "Langfuse host": s.langfuse_host,
        "Output dir": s.output_dir,
        "Log level": s.log_level,
    }
    for key, value in rows.items():
        table.add_row(key, value)
    console.print(table)


def main() -> None:  # pragma: no cover - console-script shim
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
