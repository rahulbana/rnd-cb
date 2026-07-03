"""Registry of all available reviewers, in canonical report order."""

from __future__ import annotations

from typing import Dict, List, Type

from .base import Reviewer
from .best_practices import BestPracticesReviewer
from .code_quality import CodeQualityReviewer
from .data_validation import DataValidationReviewer
from .dependency import DependencyReviewer
from .documentation import DocumentationReviewer
from .error_handling import ErrorHandlingReviewer
from .exception_handling import ExceptionHandlingReviewer
from .memory import MemoryReviewer
from .performance import PerformanceReviewer
from .readability import ReadabilityReviewer
from .resource_management import ResourceManagementReviewer
from .security import SecurityReviewer
from .syntax import SyntaxReviewer
from .type_safety import TypeSafetyReviewer

# Canonical order in which reviewers appear in reports and prompts.
REVIEWER_CLASSES: List[Type[Reviewer]] = [
    SyntaxReviewer,
    ErrorHandlingReviewer,
    ExceptionHandlingReviewer,
    TypeSafetyReviewer,
    DataValidationReviewer,
    BestPracticesReviewer,
    PerformanceReviewer,
    MemoryReviewer,
    ResourceManagementReviewer,
    SecurityReviewer,
    CodeQualityReviewer,
    ReadabilityReviewer,
    DocumentationReviewer,
    DependencyReviewer,
]


def all_reviewer_classes() -> List[Type[Reviewer]]:
    """Return every registered reviewer class in canonical order."""

    return list(REVIEWER_CLASSES)


def reviewer_classes_by_key() -> Dict[str, Type[Reviewer]]:
    """Return a ``key -> reviewer class`` mapping for lookups."""

    return {cls.key: cls for cls in REVIEWER_CLASSES}


def reviewer_keys() -> List[str]:
    """Return every registered reviewer key in canonical order."""

    return [cls.key for cls in REVIEWER_CLASSES]
