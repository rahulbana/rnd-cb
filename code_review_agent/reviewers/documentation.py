"""Documentation reviewer."""

from .base import Reviewer


class DocumentationReviewer(Reviewer):
    """The Documentation perspective."""

    key = "documentation"
    title = "Documentation"
    guidance = (
        "Every module, class, method and function MUST have a docstring. "
        "Treat a missing docstring as a definite issue (status = 1) and "
        "emit one issue per undocumented symbol. This is an objective, "
        "non-negotiable check: report it even for short, trivial, one-line, "
        "or self-explanatory functions, for private/helper functions, and "
        "for the module-level docstring at the very top of the file. Do NOT "
        "skip a missing docstring on the grounds that the code is simple or "
        "obvious. Docstrings should follow PEP 257 (imperative one-line "
        "summary, blank line before any longer body) and, where the symbol "
        "takes parameters, returns a value, or raises exceptions, document "
        "them (Args/Returns/Raises or an equivalent style). Also flag "
        "empty, placeholder ('TODO'), or stale docstrings that no longer "
        "match the code, non-obvious logic that lacks explanatory comments, "
        "and comments that are misleading or redundant. When suggesting a "
        "fix, provide the exact docstring or comment text to add."
    )
