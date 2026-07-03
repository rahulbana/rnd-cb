"""Error Handling reviewer."""

from .base import Reviewer


class ErrorHandlingReviewer(Reviewer):
    """The Error Handling perspective."""

    key = "error_handling"
    title = "Error Handling"
    guidance = (
        "Check for: missing try/except around fallible operations; try "
        "blocks that are too large or wrap unrelated code; swallowed "
        "exceptions (caught then ignored); bare `except:`; incorrect "
        "exception hierarchy ordering; raising generic `Exception`; missing "
        "`finally`; missing cleanup of resources on error paths; incorrect "
        "re-raise (losing the original traceback, e.g. `raise e` vs bare "
        "`raise`)."
    )
