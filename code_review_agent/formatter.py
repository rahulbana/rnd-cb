"""Rendering of review reports in different output formats."""

from __future__ import annotations

import json
from typing import List

from .models import FileReview, ReviewReport

# ANSI colour codes (disabled automatically when output is not a TTY).
_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_DIM = "\033[2m"

_SEVERITY_COLOR = {
    "critical": _RED,
    "high": _RED,
    "medium": _YELLOW,
    "low": _YELLOW,
    "none": _GREEN,
}


def to_json(report: ReviewReport, *, indent: int = 2) -> str:
    """Full structured report as JSON."""

    return json.dumps(report.to_dict(), indent=indent)


def to_review_json(report: ReviewReport, *, indent: int = 2) -> str:
    """Compact form matching the requested review contract.

    * Single file -> just the ``review`` object.
    * Multiple files -> a list of ``{file, review}`` objects.
    """

    if len(report.reviews) == 1:
        payload = report.reviews[0].to_dict()["review"]
    else:
        payload = [
            {"file": r.file, "review": r.to_dict()["review"]} for r in report.reviews
        ]
    return json.dumps(payload, indent=indent)


def to_pretty(report: ReviewReport, *, color: bool = True) -> str:
    """Human-friendly, colourised console report."""

    def c(text: str, code: str) -> str:
        return f"{code}{text}{_RESET}" if color else text

    lines: List[str] = []
    lines.append(c(f"Code Review Report  ({report.model})", _BOLD))
    lines.append(c(f"Target: {report.target}", _DIM))
    lines.append("")

    for review in report.reviews:
        lines.extend(_format_file(review, c, color))
        lines.append("")

    summary = (
        f"Files reviewed: {len(report.reviews)}  |  "
        f"With issues: {report.files_with_issues}  |  "
        f"Total issues: {report.total_issues}  |  "
        f"Failed: {report.failed_files}"
    )
    lines.append(c("-" * len(summary), _DIM))
    lines.append(c(summary, _BOLD))
    return "\n".join(lines)


def _format_file(review: FileReview, c, color: bool) -> List[str]:
    lines: List[str] = []
    if review.error:
        header = f"✗ {review.file}"
        lines.append(c(header, _RED))
        lines.append(f"    error: {review.error}")
        return lines

    marker = "✓" if review.ok else "!"
    header_color = _GREEN if review.ok else _YELLOW
    lines.append(c(f"{marker} {review.file}", header_color))

    for key, finding in review.findings.items():
        if finding.status == 0:
            symbol = c("PASS", _GREEN)
            lines.append(f"    [{symbol}] {key}")
        else:
            sev = finding.severity
            sev_col = _SEVERITY_COLOR.get(sev, _YELLOW)
            symbol = c(f"FAIL/{sev}", sev_col)
            lines.append(f"    [{symbol}] {key}")
            if finding.explanation:
                lines.append(f"        {c('why:', _CYAN)} {finding.explanation}")
            if finding.suggestion:
                lines.append(f"        {c('fix:', _CYAN)} {finding.suggestion}")
            for issue in finding.issues:
                lines.extend(_format_issue(issue, c))
    return lines


def _format_issue(issue, c) -> List[str]:
    out: List[str] = []
    loc = _location(issue)
    header = f"        - {loc}".rstrip()
    out.append(header)
    if issue.explanation:
        out.append(f"          {issue.explanation}")
    if issue.current_code:
        out.append(f"          {c('current:', _CYAN)}")
        for ln in issue.current_code.splitlines() or [""]:
            out.append(c(f"          - {ln}", _RED))
    if issue.suggested_code:
        label = "add:" if not issue.current_code else "suggested:"
        out.append(f"          {c(label, _CYAN)}")
        for ln in issue.suggested_code.splitlines() or [""]:
            out.append(c(f"          + {ln}", _GREEN))
    return out


def _location(issue) -> str:
    if issue.line and issue.end_line and issue.end_line != issue.line:
        return f"lines {issue.line}-{issue.end_line}:"
    if issue.line:
        return f"line {issue.line}:"
    return "suggested addition:"


def render(report: ReviewReport, fmt: str, *, color: bool = True) -> str:
    """Dispatch to the requested output format."""

    if fmt == "json":
        return to_json(report)
    if fmt == "review":
        return to_review_json(report)
    if fmt == "pretty":
        return to_pretty(report, color=color)
    raise ValueError(f"Unknown output format: {fmt}")
