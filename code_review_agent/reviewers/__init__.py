"""Reviewer package: one self-contained perspective per module.

Public surface:

* :class:`~code_review_agent.reviewers.base.Reviewer` — the base class.
* :func:`~code_review_agent.reviewers.registry.all_reviewer_classes`,
  :func:`~code_review_agent.reviewers.registry.reviewer_classes_by_key`,
  :func:`~code_review_agent.reviewers.registry.reviewer_keys` — the registry.
"""

from __future__ import annotations

from .base import Reviewer
from .registry import (
    all_reviewer_classes,
    reviewer_classes_by_key,
    reviewer_keys,
)

__all__ = [
    "Reviewer",
    "all_reviewer_classes",
    "reviewer_classes_by_key",
    "reviewer_keys",
]
