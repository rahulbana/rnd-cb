"""Render a FactCheckReport to the terminal (or JSON)."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import FactCheckReport, Stance, Verdict

_VERDICT_STYLE = {
    Verdict.TRUE: ("✓ TRUE", "bold white on green"),
    Verdict.FALSE: ("✗ FALSE", "bold white on red"),
    Verdict.PARTIALLY_TRUE: ("◑ PARTIALLY TRUE", "bold black on yellow"),
    Verdict.UNVERIFIED: ("? UNVERIFIED", "bold white on grey37"),
}

_STANCE_STYLE = {
    Stance.SUPPORTS: ("SUPPORTS", "green"),
    Stance.REFUTES: ("REFUTES", "red"),
    Stance.NEUTRAL: ("NEUTRAL", "yellow"),
}


def render_report(report: FactCheckReport, console: Console | None = None) -> None:
    console = console or Console()
    result = report.result

    label, style = _VERDICT_STYLE[result.verdict]
    header = Text.assemble(
        (f" {label} ", style),
        ("   confidence: ", "dim"),
        (f"{result.confidence:.0%}", "bold"),
    )

    console.print()
    console.print(Panel(Text(report.claim, style="bold"), title="Claim", border_style="cyan"))
    console.print(header)
    console.print()
    console.print(Panel(result.summary, title="Conclusion", border_style="cyan"))

    if result.key_findings:
        findings = Text()
        for finding in result.key_findings:
            findings.append("• ", style="cyan")
            findings.append(finding + "\n")
        console.print(Panel(findings, title="Key findings (from sources)", border_style="cyan"))

    _render_sources(report, console)


def _render_sources(report: FactCheckReport, console: Console) -> None:
    stance_by_index = {a.index: a for a in report.result.source_assessments}

    table = Table(title="Sources", show_lines=False, header_style="bold")
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Stance", no_wrap=True)
    table.add_column("Title")
    table.add_column("URL", style="blue")

    for source in report.sources:
        assessment = stance_by_index.get(source.index)
        if assessment is not None:
            stance_label, stance_style = _STANCE_STYLE[assessment.stance]
            stance_text = Text(stance_label, style=stance_style)
        else:
            stance_text = Text("—", style="dim")
        table.add_row(str(source.index), stance_text, source.title, source.url)

    console.print()
    console.print(table)

    notes = [
        (a.index, a.note)
        for a in report.result.source_assessments
        if a.note.strip()
    ]
    if notes:
        console.print()
        for index, note in sorted(notes):
            console.print(Text.assemble((f"[{index}] ", "bold cyan"), (note, "dim")))
