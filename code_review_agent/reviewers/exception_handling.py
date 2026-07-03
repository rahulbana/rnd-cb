"""Exception Handling reviewer."""

from .base import Reviewer


class ExceptionHandlingReviewer(Reviewer):
    """The Exception Handling perspective."""

    key = "exception_handling"
    title = "Exception Handling"
    guidance = (
        "Check that exceptions are specific rather than broad; that custom "
        "exception types are defined and used where appropriate; and that "
        "exception chaining (`raise ... from ...`) is used to preserve "
        "context."
    )
