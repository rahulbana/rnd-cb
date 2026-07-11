"""Command-line interface for Deep Agent.

Examples::

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
) -> None:
    """Run the full research pipeline and save a markdown report."""

    setup_logging()
    console.print(
        Panel.fit(f"[bold cyan]Deep research[/]: {topic}", border_style="cyan")
    )
    try:
        report = run_research(topic, max_iterations=iterations)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Research failed")
        console.print(f"[bold red]Error:[/] {exc}")
        raise typer.Exit(code=1)

    path = save_report(report, output_dir=output_dir)
    console.print(
        Panel.fit(
            f"[bold green]Report written[/] → {path}\n"
            f"Sources cited: {len(report.citations)}",
            border_style="green",
        )
    )


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
        "Search provider": s.search_provider.value,
        "Search max results": str(s.search_max_results),
        "Max iterations": str(s.max_research_iterations),
        "Scrape concurrency": str(s.scrape_max_concurrency),
        "Celery eager": str(s.celery_task_always_eager),
        "Celery broker": s.celery_broker_url,
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
