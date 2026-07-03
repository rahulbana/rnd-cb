"""Data models used across the code review agent.

The public review contract is intentionally small and stable. Each perspective
maps to a category object:

    {
        "security": {
            "status": 0|1,
            "severity": "none|low|medium|high|critical",
            "explanation": str,
            "suggestion": str,
            "issues": [
                {
                    "line": int|null,
                    "end_line": int|null,
                    "explanation": str,
                    "current_code": str,     # exact code to change ("" if pure addition)
                    "suggested_code": str    # exact code to add / replace with
                },
                ...
            ]
        },
        ...
    }

Status convention
-----------------
* ``status = 1`` -> an issue was found for this category (needs attention).
* ``status = 0`` -> no issue found for this category (clean).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Human-friendly severity ranking for a flagged category."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Ordering used to compute the "worst" severity across a category's issues.
SEVERITY_ORDER = {
    Severity.NONE.value: 0,
    Severity.LOW.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.HIGH.value: 3,
    Severity.CRITICAL.value: 4,
}


@dataclass
class Issue:
    """A single concrete problem with an exact code fix."""

    explanation: str = ""
    line: Optional[int] = None
    end_line: Optional[int] = None
    current_code: str = ""  # exact existing snippet ("" for pure additions)
    suggested_code: str = ""  # exact code to add / replace the current snippet
    severity: str = Severity.MEDIUM.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "end_line": self.end_line,
            "severity": self.severity,
            "explanation": self.explanation,
            "current_code": self.current_code,
            "suggested_code": self.suggested_code,
        }


@dataclass
class CategoryFinding:
    """Result for a single category of a single file."""

    status: int  # 1 = issue found, 0 = clean
    explanation: str = ""
    suggestion: str = ""
    severity: str = Severity.NONE.value
    issues: List[Issue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": int(self.status),
            "severity": self.severity,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass
class FileReview:
    """Aggregated review of a single file."""

    file: str
    language: str
    findings: Dict[str, CategoryFinding] = field(default_factory=dict)
    error: str = ""  # populated when the file could not be reviewed

    @property
    def issue_count(self) -> int:
        return sum(1 for f in self.findings.values() if f.status == 1)

    @property
    def ok(self) -> bool:
        return not self.error and self.issue_count == 0

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "file": self.file,
            "language": self.language,
            "issue_count": self.issue_count,
        }
        if self.error:
            payload["error"] = self.error
        payload["review"] = {
            key: finding.to_dict() for key, finding in self.findings.items()
        }
        return payload


@dataclass
class ReviewReport:
    """Top-level report covering one or more files."""

    target: str
    model: str
    reviews: List[FileReview] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return sum(r.issue_count for r in self.reviews)

    @property
    def files_with_issues(self) -> int:
        return sum(1 for r in self.reviews if r.issue_count > 0)

    @property
    def failed_files(self) -> int:
        return sum(1 for r in self.reviews if r.error)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "model": self.model,
            "summary": {
                "files_reviewed": len(self.reviews),
                "files_with_issues": self.files_with_issues,
                "files_failed": self.failed_files,
                "total_issues": self.total_issues,
            },
            "results": [r.to_dict() for r in self.reviews],
        }
