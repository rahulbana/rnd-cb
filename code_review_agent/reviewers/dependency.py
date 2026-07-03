"""Dependency Review reviewer."""

from .base import Reviewer


class DependencyReviewer(Reviewer):
    """The Dependency Review perspective."""

    key = "dependency"
    title = "Dependency Review"
    guidance = (
        "Using the PROJECT DEPENDENCIES manifest block when present, check "
        "for: packages imported but not declared, and packages declared but "
        "unused; outdated packages; known CVEs / vulnerable versions (based "
        "on your knowledge — say so if unsure); duplicate packages; version "
        "conflicts; and requirements.txt hygiene (unpinned or loosely "
        "pinned versions). Do not fabricate CVE identifiers."
    )
