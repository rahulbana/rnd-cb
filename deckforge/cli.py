"""DeckForge command-line interface.

Run from a terminal — no web UI. Source material comes from a file, stdin
(pasted text), or the ``--text`` flag. Example:

    python -m deckforge --file report.pdf --topic "Q3 results" --theme auto
    pbpaste | python -m deckforge --topic "Launch plan"
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from .config import get_settings
from .deck.themes import THEMES
from .graph import generate_deck
from .ingestion import load_source, load_text

console = Console()


def _read_source(file: str | None, text: str | None) -> str:
    """Resolve source material from --file, --text, or piped stdin."""
    if file:
        return load_source(file)
    if text:
        return load_text(text)
    if not sys.stdin.isatty():  # piped / pasted input
        piped = sys.stdin.read()
        if piped.strip():
            return load_text(piped)
    raise click.UsageError(
        "No source provided. Use --file PATH, --text \"...\", or pipe text "
        "via stdin (e.g. `cat notes.txt | python -m deckforge --topic ...`)."
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--file", "-f", type=click.Path(exists=True, dir_okay=False),
              help="Source document: .pdf, .docx, .txt or .md")
@click.option("--text", "-x", help="Inline source text (alternative to --file).")
@click.option("--topic", "-t", default="",
              help="Topic / instruction to steer the deck.")
@click.option("--theme", default=None,
              type=click.Choice([*THEMES.keys(), "auto"], case_sensitive=False),
              help="Visual theme, or 'auto' to let the design agent choose.")
@click.option("--slides", "-n", "target_slides", default=10, show_default=True,
              help="Approximate number of slides to generate.")
def main(file, text, topic, theme, target_slides):
    """Generate a colorful PowerPoint deck from documents + web research."""
    settings = get_settings()

    console.print(
        Panel.fit(
            "[bold cyan]DeckForge[/]  ·  multi-agent deck generator\n"
            f"model=[green]{settings.model}[/]  "
            f"research=[green]{'on' if settings.research_enabled else 'off'}[/]  "
            f"theme=[green]{theme or settings.theme}[/]",
            border_style="cyan",
        )
    )

    try:
        source = _read_source(file, text)
    except (click.UsageError, FileNotFoundError, ValueError) as exc:
        console.print(f"[red]✗[/] {exc}")
        raise SystemExit(2)

    if not topic:
        # Derive a working topic from the first line of source if absent.
        topic = source.strip().splitlines()[0][:120] if source.strip() else "Presentation"
        console.print(f"[dim]No --topic given; inferring: “{topic}”[/]")

    def progress(msg: str) -> None:
        console.print(f"  [cyan]›[/] {msg}")

    try:
        path: Path = generate_deck(
            topic=topic,
            source=source,
            theme=theme,
            target_slides=target_slides,
            settings=settings,
            progress=progress,
        )
    except RuntimeError as exc:  # e.g. missing OPENAI_API_KEY
        console.print(f"[red]✗[/] {exc}")
        raise SystemExit(1)

    console.print(
        Panel.fit(
            f"[bold green]✓ Deck ready[/]\n[white]{path}[/]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
