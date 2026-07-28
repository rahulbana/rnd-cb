"""Command-line interface for the dataset generator.

Examples::

    python -m app.cli plan "fraud detection dataset with 2% fraud rate"
    python -m app.cli generate "telecom churn dataset with 50000 customers and 12% churn" \
        --rows 50000 --format csv --format parquet
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from app.config import settings
from app.services.generator import DatasetService
from app.utils.logging import configure_logging

app = typer.Typer(add_completion=False, help="ML Dataset Generator Agent")


@app.command()
def plan(
    prompt: str,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show each planning step."
    ),
) -> None:
    """Show the dataset plan inferred from PROMPT without generating data."""

    configure_logging(verbose)
    spec = DatasetService().plan(prompt)
    typer.echo(json.dumps(spec.model_dump(mode="json"), indent=2))


@app.command()
def generate(
    prompt: str,
    rows: int = typer.Option(None, help="Override the inferred row count."),
    seed: int = typer.Option(None, help="Random seed for reproducibility."),
    fmt: list[str] = typer.Option(
        ["csv"], "--format", "-f", help="Export format(s): csv, parquet, json, excel, sqlite, sql."
    ),
    out_dir: Path = typer.Option(None, help="Output directory (default: ./datasets)."),
    fast: bool = typer.Option(
        False, help="Skip validation/EDA/evaluation for a quick generate-only run."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show each pipeline step as it runs."
    ),
) -> None:
    """Generate a full dataset from PROMPT."""

    configure_logging(verbose)
    settings.ensure_dirs()
    service = DatasetService()
    result = service.generate_from_prompt(
        prompt,
        rows=rows,
        seed=seed,
        formats=fmt,
        out_dir=out_dir,
        full=not fast,
    )
    typer.echo(json.dumps(result.summary(), indent=2, default=str))


@app.command()
def scenarios() -> None:
    """List the built-in domain scenario templates."""

    from app.prompts.scenarios import SCENARIOS

    for key, cfg in SCENARIOS.items():
        typer.echo(f"{key:16s} {cfg['task_type'].value:28s} {cfg['domain']}")


if __name__ == "__main__":
    app()
