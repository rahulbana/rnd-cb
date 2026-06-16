"""Core data models shared across the reviewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    """Severity of a single finding, ordered from most to least serious."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        return order[self]

    @classmethod
    def coerce(cls, value: str) -> "Severity":
        """Best-effort parse of a severity string returned by the model."""
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return cls.MEDIUM


@dataclass
class Finding:
    """A single issue raised by a review agent."""

    title: str
    description: str
    severity: Severity = Severity.MEDIUM
    line: Optional[int] = None
    recommendation: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Finding":
        line = data.get("line")
        try:
            line = int(line) if line not in (None, "", "null") else None
        except (TypeError, ValueError):
            line = None
        return cls(
            title=str(data.get("title", "")).strip() or "Untitled finding",
            description=str(data.get("description", "")).strip(),
            severity=Severity.coerce(data.get("severity", "medium")),
            line=line,
            recommendation=str(data.get("recommendation", "")).strip(),
        )


@dataclass
class CategoryResult:
    """All findings produced by one agent for one file."""

    category: str
    file_path: str
    findings: List[Finding] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None


@dataclass
class FileReview:
    """Aggregated results for a single file across every category."""

    file_path: str
    results: List[CategoryResult] = field(default_factory=list)

    @property
    def findings(self) -> List[Finding]:
        out: List[Finding] = []
        for result in self.results:
            out.extend(result.findings)
        return out


@dataclass
class ReviewReport:
    """The full review across every file and category."""

    root: str
    language: str
    model: str
    files: List[FileReview] = field(default_factory=list)

    @property
    def all_findings(self) -> List[Finding]:
        out: List[Finding] = []
        for file_review in self.files:
            out.extend(file_review.findings)
        return out

    def severity_counts(self) -> dict:
        counts = {sev: 0 for sev in Severity}
        for finding in self.all_findings:
            counts[finding.severity] += 1
        return counts
