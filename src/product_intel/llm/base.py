"""The LLM interface the reasoning agents depend on.

Rather than a raw ``complete(prompt)`` call (which forces brittle response
parsing), the interface exposes the handful of high-level reasoning tasks the
pipeline actually needs. Both the offline and Anthropic clients implement these,
so agents never branch on provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence, Tuple


class LLMClient(ABC):
    #: human-readable provider name, surfaced in reports for provenance.
    name: str = "base"

    @abstractmethod
    def summarize_gap(self, feature: str, negative_quotes: Sequence[str]) -> str:
        """One-sentence description of why an advertised feature underdelivers."""

    @abstractmethod
    def propose_action(self, title: str, category: str, quotes: Sequence[str]) -> str:
        """A concrete engineering/hardware remediation for an issue."""

    @abstractmethod
    def draft_user_story(
        self, title: str, kind: str, evidence: Sequence[str]
    ) -> Tuple[str, List[str]]:
        """Return a (user_story, acceptance_criteria) pair for a backlog ticket."""
