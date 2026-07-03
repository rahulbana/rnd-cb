"""Performance Review reviewer."""

from .base import Reviewer


class PerformanceReviewer(Reviewer):
    """The Performance Review perspective."""

    key = "performance"
    title = "Performance Review"
    guidance = (
        "Check for: nested loops with poor complexity; repeated DB calls "
        "(N+1); repeated API calls; regex compiled inside loops instead of "
        "once; large memory allocations; costly sorting; repeated object "
        "creation; inefficient string concatenation in loops; repeated JSON "
        "parsing; and repeatedly opening the same file."
    )
