"""Resource Management reviewer."""

from .base import Reviewer


class ResourceManagementReviewer(Reviewer):
    """The Resource Management perspective."""

    key = "resource_management"
    title = "Resource Management"
    guidance = (
        "Check that files, database handles, network connections, sockets "
        "and threads are always released: prefer context managers (`with`) "
        "over manual close, ensure cleanup on every path, and verify "
        "threads/pools are joined or shut down."
    )
