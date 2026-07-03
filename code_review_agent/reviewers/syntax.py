"""Syntax Review reviewer."""

from .base import Reviewer


class SyntaxReviewer(Reviewer):
    """The Syntax Review perspective."""

    key = "syntax"
    title = "Syntax Review"
    guidance = (
        "Check for: syntax errors; invalid or inconsistent indentation; "
        "missing imports (names used but never imported); circular imports; "
        "unused imports; duplicate imports; invalid or misapplied "
        "decorators."
    )
