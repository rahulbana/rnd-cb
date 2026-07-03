"""Data models used across the code review agent.

The public review contract is intentionally small and stable:

    {
        "security":     {"status": 0|1, "explanation": str, "suggestion": str},
        "data_type":    {"status": 0|1, "explanation": str, "suggestion": str},
        "harmful_code": {"status": 0|1, "explanation": str, "suggestion": str},
        ...
    }

Status convention
-----------------
* ``status = 1`` -> an issue was found for this category (needs attention).
* ``status = 0`` -> no issue found for this category (clean).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List


class Severity(str, Enum):
    """Human-friendly severity ranking for a flagged category."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ReviewCategory:
    """Definition of a single perspective the reviewer evaluates."""

    key: str
    title: str
    guidance: str


@dataclass
class CategoryFinding:
    """Result for a single category of a single file."""

    status: int  # 1 = issue found, 0 = clean
    explanation: str = ""
    suggestion: str = ""
    severity: str = Severity.NONE.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": int(self.status),
            "severity": self.severity,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
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
