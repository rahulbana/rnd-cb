"""Command-line entry point for the code reviewer."""

from __future__ import annotations

import os
import sys
from typing import List, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from .agents import build_agents, default_category_keys
from .collector import collect_files
from .config import Settings
from .llm import LLMClient
from .orchestrator import run_review
from .report import render_report

app = typer.Typer(
    add_completion=False,
    help="AI-powered multi-agent code reviewer (OpenAI).",
)

console = Console()
err_console = Console(stderr=True)


@app.command()
def review(
    path: str = typer.Argument(
        ..., help="Path to the directory (or file) containing the code."
    ),
    language: str = typer.Option(
        ..., "--language", "-l", help="Programming language of the code."
    ),
    model: str = typer.Option(
        "gpt-4o-mini", "--model", "-m", help="OpenAI model to use."
    ),
    categories: Optional[List[str]] = typer.Option(
        None,
        "--category",
        "-c",
        help=(
            "Limit review to specific categories (repeatable). "
            "Default: all categories."
        ),
    ),
    max_file_bytes: int = typer.Option(
        60_000, help="Truncate files larger than this many bytes."
    ),
    max_workers: int = typer.Option(
        8, help="Max concurrent LLM calls."
    ),
    markdown: Optional[str] = typer.Option(
        None,
        "--markdown",
        "--md",
        help="Also write a Markdown report to this path.",
    ),
    docx: Optional[str] = typer.Option(
        None, "--docx", help="Also write a Word (.docx) report to this path."
    ),
) -> None:
    """Review the code at PATH and print findings to the console."""
    load_dotenv()

    if not os.environ.get("OPENAI_API_KEY"):
        err_console.print(
            "[red]Error:[/red] OPENAI_API_KEY is not set. "
            "Export it or add it to a .env file."
        )
        raise typer.Exit(code=2)

    try:
        settings = Settings(
            path=path,
            language=language,
            model=model,
            max_file_bytes=max_file_bytes,
            max_workers=max_workers,
        )
        agents = build_agents(categories or default_category_keys())
        files = collect_files(settings)
    except (ValueError, FileNotFoundError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2)

    if not files:
        err_console.print(
            f"[yellow]No {language} files found under {path}.[/yellow]"
        )
        raise typer.Exit(code=1)

    total = len(files) * len(agents)
    console.print(
        f"Reviewing [bold]{len(files)}[/bold] file(s) across "
        f"[bold]{len(agents)}[/bold] categor(ies) "
        f"([bold]{total}[/bold] checks)…"
    )

    client = LLMClient(settings.model)
    completed = {"n": 0}

    with console.status("[bold]Running review agents…[/bold]") as status:

        def on_progress(file_path: str, category: str) -> None:
            completed["n"] += 1
            status.update(
                f"[bold]Running review agents…[/bold] "
                f"{completed['n']}/{total} "
                f"({category} · {file_path})"
            )

        report = run_review(
            settings, files, agents, client=client, on_progress=on_progress
        )

    render_report(report, console)

    if markdown:
        from .exporters import write_markdown

        write_markdown(report, markdown)
        console.print(f"[green]✓[/green] Markdown report written to {markdown}")

    if docx:
        from .exporters import write_docx

        write_docx(report, docx)
        console.print(f"[green]✓[/green] Word report written to {docx}")

    # Exit non-zero if any critical/high findings exist (useful for CI).
    counts = report.severity_counts()
    from .models import Severity

    if counts[Severity.CRITICAL] or counts[Severity.HIGH]:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
