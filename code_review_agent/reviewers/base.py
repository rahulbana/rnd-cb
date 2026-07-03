"""Base class shared by every reviewer.

A *reviewer* is a self-contained perspective the agent evaluates (security,
documentation, performance, ...). Each concrete reviewer lives in its own
module and subclasses :class:`Reviewer`, defining its ``key``, ``title`` and
``guidance``. Keeping one class per reviewer makes the set easy to extend,
test, and configure independently — including giving a reviewer its own LLM
model via ``default_model`` or per-run configuration.
"""

from __future__ import annotations

from typing import Optional


class Reviewer:
    """A single review perspective.

    Subclasses override the class attributes. Instances may carry a per-run
    ``model`` override (e.g. from ``reviewers.yaml``); when unset the engine
    uses the run's default model.
    """

    #: Stable machine key used in output and configuration (e.g. ``"security"``).
    key: str = ""
    #: Human-readable title shown in reports.
    title: str = ""
    #: Instructions handed to the model describing what to check.
    guidance: str = ""
    #: Optional per-reviewer default model; ``None`` means "use the run default".
    default_model: Optional[str] = None

    def __init__(self, model: Optional[str] = None) -> None:
        """Create a reviewer, optionally overriding its LLM model for this run."""

        self.model = model or self.default_model

    def prompt_line(self) -> str:
        """Return this reviewer's one-line description for the review prompt."""

        return f'- "{self.key}" ({self.title}): {self.guidance}'

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Reviewer {self.key} model={self.model!r}>"
