"""Deterministic, template-based LLM used by default.

Produces sensible, structured text for the synthesis agents without any network
call or API key, so the whole pipeline runs and is testable offline. The output
is intentionally plain and reproducible - upgrade to :class:`AnthropicLLM` for
fluent, context-aware prose.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .base import LLMClient


def _first_quote(quotes: Sequence[str], limit: int = 140) -> str:
    for q in quotes:
        q = q.strip()
        if q:
            return q if len(q) <= limit else q[: limit - 1].rstrip() + "…"
    return ""


class OfflineLLM(LLMClient):
    name = "offline-deterministic"

    def summarize_gap(self, feature: str, negative_quotes: Sequence[str]) -> str:
        evidence = _first_quote(negative_quotes)
        base = f"Users report that '{feature}' does not meet expectations"
        if evidence:
            return f"{base}: e.g. \"{evidence}\"."
        return base + "."

    def propose_action(self, title: str, category: str, quotes: Sequence[str]) -> str:
        cat = category.lower()
        if "blocker" in cat:
            verb = "Root-cause and fix"
        elif "usability" in cat:
            verb = "Redesign the interaction for"
        else:
            verb = "Refine the finish/materials for"
        return (
            f"{verb} the issue behind '{title}'. Reproduce from the reported "
            f"conditions, add regression coverage, and validate against the "
            f"affected user scenarios before release."
        )

    def draft_user_story(
        self, title: str, kind: str, evidence: Sequence[str]
    ) -> Tuple[str, List[str]]:
        if kind.lower().startswith("defect"):
            story = (
                f"As a customer, I want '{title}' resolved so that the product "
                f"performs reliably in everyday use."
            )
            criteria = [
                "The reported failure no longer reproduces under the documented conditions.",
                "Automated regression test covers the scenario.",
                "Negative reviews citing this issue drop in the next release cohort.",
            ]
        else:
            story = (
                f"As a customer, I want '{title}' so that the product better fits "
                f"how I actually use it."
            )
            criteria = [
                "The enhancement is available and discoverable to users.",
                "It measurably addresses the demand seen in reviews.",
                "No regression to existing core-strength features.",
            ]
        return story, criteria
