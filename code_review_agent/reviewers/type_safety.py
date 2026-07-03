"""Type Safety reviewer."""

from .base import Reviewer


class TypeSafetyReviewer(Reviewer):
    """The Type Safety perspective."""

    key = "type_safety"
    title = "Type Safety"
    guidance = (
        "Check for missing type hints on functions, parameters, returns and "
        "important variables. Using the DEPENDENCY DEFINITIONS block when "
        "present, flag calls whose argument or return types are "
        "inconsistent with the callee's signature."
    )
