"""Render a ReviewReport as a rich console report."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .models import ReviewReport, Severity

_SEVERITY_STYLE = {
    Severity.CRITICAL: "bold white on red",
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}

_SEVERITY_LABEL = {
    Severity.CRITICAL: "CRITICAL",
    Severity.HIGH: "HIGH",
    Severity.MEDIUM: "MEDIUM",
    Severity.LOW: "LOW",
    Severity.INFO: "INFO",
}


def render_report(report: ReviewReport, console: Console | None = None) -> None:
    console = console or Console()

    console.print()
    console.print(
        Panel.fit(
            f"[bold]AI Code Review[/bold]\n"
            f"Path: {report.root}\n"
            f"Language: {report.language}\n"
            f"Model: {report.model}",
            border_style="blue",
        )
    )

    _render_summary(report, console)

    for file_review in report.files:
        findings = file_review.findings
        errors = [r for r in file_review.results if r.error]
        if not findings and not errors:
            console.print(
                f"\n[green]✓[/green] [bold]{file_review.file_path}[/bold] "
                "— no issues found."
            )
            continue

        console.print()
        console.print(Rule(f"[bold]{file_review.file_path}[/bold]"))

        for result in file_review.results:
            if result.error:
                console.print(
                    f"  [red]![/red] {result.category}: "
                    f"review failed ({result.error})"
                )
                continue
            if not result.findings:
                continue

            console.print(
                f"\n[bold underline]{result.category}[/bold underline]"
            )
            for finding in sorted(
                result.findings, key=lambda f: f.severity.rank
            ):
                _render_finding(finding, console)

    console.print()


def _render_summary(report: ReviewReport, console: Console) -> None:
    counts = report.severity_counts()
    table = Table(title="Summary", title_style="bold", show_edge=True)
    table.add_column("Severity")
    table.add_column("Count", justify="right")
    for sev in Severity:
        table.add_row(
            Text(_SEVERITY_LABEL[sev], style=_SEVERITY_STYLE[sev]),
            str(counts[sev]),
        )
    table.add_row(
        Text("TOTAL", style="bold"),
        Text(str(len(report.all_findings)), style="bold"),
    )
    console.print()
    console.print(table)
    console.print(
        f"Files reviewed: [bold]{len(report.files)}[/bold]"
    )


def _render_finding(finding, console: Console) -> None:
    badge = Text(
        f" {_SEVERITY_LABEL[finding.severity]} ",
        style=_SEVERITY_STYLE[finding.severity],
    )
    location = f" (line {finding.line})" if finding.line else ""
    header = Text.assemble(badge, Text(f" {finding.title}{location}", "bold"))
    console.print(header)
    if finding.description:
        console.print(Text(f"    {finding.description}"))
    if finding.recommendation:
        console.print(
            Text.assemble(
                Text("    → ", "green"),
                Text(finding.recommendation, "green"),
            )
        )
