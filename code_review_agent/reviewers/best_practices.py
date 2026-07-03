"""Python Best Practices reviewer."""

from .base import Reviewer


class BestPracticesReviewer(Reviewer):
    """The Python Best Practices perspective."""

    key = "best_practices"
    title = "Python Best Practices"
    guidance = (
        "Check adherence to: PEP 8 (style) and PEP 257 (docstrings); naming "
        "conventions; avoiding magic numbers; using list comprehensions, "
        "context managers, generators, `enumerate`, `zip`, the walrus "
        "operator, `match`-`case`, and f-strings where they make the code "
        "clearer and more idiomatic."
    )
