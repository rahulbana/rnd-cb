"""Optional Claude-backed LLM client.

Enabled with ``--llm anthropic`` (requires ``pip install 'product-intel[anthropic]'``
and an ``ANTHROPIC_API_KEY``). Falls back to the offline templates on any error
so a transient API problem never breaks the pipeline. The ``anthropic`` package
is imported lazily, keeping it an optional dependency.
"""

from __future__ import annotations

import json
import os
from typing import List, Sequence, Tuple

from .base import LLMClient
from .offline import OfflineLLM


class AnthropicLLM(LLMClient):
    name = "anthropic-claude"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "The 'anthropic' package is required for --llm anthropic. "
                "Install with: pip install 'product-intel[anthropic]'"
            ) from exc
        from anthropic import Anthropic

        self.model = model
        self._client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._fallback = OfflineLLM()

    # -- internal helper ---------------------------------------------------- #
    def _complete(self, system: str, prompt: str, max_tokens: int = 512) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in resp.content if block.type == "text").strip()

    # -- interface ---------------------------------------------------------- #
    def summarize_gap(self, feature: str, negative_quotes: Sequence[str]) -> str:
        try:
            quotes = "\n".join(f"- {q}" for q in list(negative_quotes)[:6])
            return self._complete(
                system="You are a product analyst. Reply with ONE concise sentence.",
                prompt=(
                    f"Advertised feature: {feature}\n"
                    f"Representative negative reviews:\n{quotes}\n\n"
                    "In one sentence, explain the gap between the promise and the "
                    "real-world experience."
                ),
                max_tokens=120,
            )
        except Exception:  # pragma: no cover - network/runtime guard
            return self._fallback.summarize_gap(feature, negative_quotes)

    def propose_action(self, title: str, category: str, quotes: Sequence[str]) -> str:
        try:
            quotes_txt = "\n".join(f"- {q}" for q in list(quotes)[:6])
            return self._complete(
                system="You are a senior engineer proposing a fix. Reply with 1-2 sentences.",
                prompt=(
                    f"Issue: {title}\nCategory: {category}\n"
                    f"Evidence:\n{quotes_txt}\n\n"
                    "Propose a concrete engineering or hardware remediation."
                ),
                max_tokens=160,
            )
        except Exception:  # pragma: no cover
            return self._fallback.propose_action(title, category, quotes)

    def draft_user_story(
        self, title: str, kind: str, evidence: Sequence[str]
    ) -> Tuple[str, List[str]]:
        try:
            ev = "\n".join(f"- {q}" for q in list(evidence)[:6])
            raw = self._complete(
                system=(
                    "You are a product manager. Respond with strict JSON: "
                    '{"user_story": string, "acceptance_criteria": [string, ...]}.'
                ),
                prompt=(
                    f"Backlog item ({kind}): {title}\nEvidence:\n{ev}\n\n"
                    "Write one user story and 2-4 acceptance criteria."
                ),
                max_tokens=400,
            )
            data = json.loads(raw)
            story = str(data["user_story"])
            criteria = [str(c) for c in data.get("acceptance_criteria", [])]
            if not criteria:
                raise ValueError("no acceptance criteria")
            return story, criteria
        except Exception:  # pragma: no cover
            return self._fallback.draft_user_story(title, kind, evidence)
