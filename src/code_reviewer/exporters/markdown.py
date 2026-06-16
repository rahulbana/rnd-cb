"""Render a ReviewReport as a Markdown document."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..models import Finding, ReviewReport, Severity

_SEVERITY_LABEL = {
    Severity.CRITICAL: "CRITICAL",
    Severity.HIGH: "HIGH",
    Severity.MEDIUM: "MEDIUM",
    Severity.LOW: "LOW",
    Severity.INFO: "INFO",
}

_SEVERITY_EMOJI = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🔵",
    Severity.INFO: "⚪",
}


def render_markdown(report: ReviewReport) -> str:
    """Return the full report as a Markdown string."""
    lines: List[str] = []
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("# AI Code Review")
    lines.append("")
    lines.append(f"- **Path:** `{report.root}`")
    lines.append(f"- **Language:** {report.language}")
    lines.append(f"- **Model:** {report.model}")
    lines.append(f"- **Files reviewed:** {len(report.files)}")
    lines.append(f"- **Generated:** {generated}")
    lines.append("")

    # Summary table.
    counts = report.severity_counts()
    lines.append("## Summary")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("| --- | ---: |")
    for sev in Severity:
        lines.append(
            f"| {_SEVERITY_EMOJI[sev]} {_SEVERITY_LABEL[sev]} | {counts[sev]} |"
        )
    lines.append(f"| **TOTAL** | **{len(report.all_findings)}** |")
    lines.append("")

    # Per-file detail.
    lines.append("## Findings")
    lines.append("")
    for file_review in report.files:
        findings = file_review.findings
        errors = [r for r in file_review.results if r.error]

        lines.append(f"### `{file_review.file_path}`")
        lines.append("")

        if not findings and not errors:
            lines.append("✓ No issues found.")
            lines.append("")
            continue

        for result in file_review.results:
            if result.error:
                lines.append(
                    f"> ⚠️ **{result.category}** review failed: {result.error}"
                )
                lines.append("")
                continue
            if not result.findings:
                continue

            lines.append(f"#### {result.category}")
            lines.append("")
            for finding in sorted(
                result.findings, key=lambda f: f.severity.rank
            ):
                lines.extend(_finding_md(finding))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _finding_md(finding: Finding) -> List[str]:
    location = f" _(line {finding.line})_" if finding.line else ""
    emoji = _SEVERITY_EMOJI[finding.severity]
    label = _SEVERITY_LABEL[finding.severity]
    out = [f"- {emoji} **[{label}] {finding.title}**{location}"]
    if finding.description:
        out.append(f"  - {finding.description}")
    if finding.recommendation:
        out.append(f"  - **Recommendation:** {finding.recommendation}")
    return out


def write_markdown(report: ReviewReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))
