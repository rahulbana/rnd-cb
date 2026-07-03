"""Memory Review reviewer."""

from .base import Reviewer


class MemoryReviewer(Reviewer):
    """The Memory Review perspective."""

    key = "memory"
    title = "Memory Review"
    guidance = (
        "Check for: unnecessarily large lists (use generators); memory "
        "leaks; cache misuse (unbounded caches); reference cycles; overuse "
        "of global variables; huge dictionaries; and copying data instead "
        "of using a view/slice/iterator."
    )
