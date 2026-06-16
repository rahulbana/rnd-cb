"""Reviewer (critic) agent.

The reviewer reads the coder's output and acts as a quality gate. It checks for
bugs, missing validation, missing/weak exception handling, and inadequate
documentation, then returns a corrected version of the code along with a list
of the issues it addressed.
"""
from __future__ import annotations

from typing import List, Tuple

from app.agents.base import AgentError, BaseAgent
from app.schemas import Language

_SYSTEM_PROMPT = (
    "You are a meticulous senior code reviewer. You are given a target "
    "language, the original problem statement, and a candidate solution.\n"
    "Review the code critically for:\n"
    "  - Correctness and obvious bugs or logic errors.\n"
    "  - Input validation (is every input checked?).\n"
    "  - Exception/error handling (are failure modes handled idiomatically?).\n"
    "  - Documentation quality (is the function clearly documented?).\n"
    "Then return an IMPROVED version of the code with every issue fixed. If the "
    "code is already correct, return it unchanged and say so.\n"
    "Respond ONLY with JSON of the form: "
    "{\"code\": \"<final corrected source code>\", "
    "\"review_notes\": [\"issue or improvement 1\", ...]}.\n"
    "review_notes must describe what you found and changed (empty list if the "
    "code was already perfect). Do NOT wrap code in markdown fences inside the "
    "JSON string."
)


class ReviewerAgent(BaseAgent):
    """Reviews and repairs the coder agent's output."""

    def __init__(self, **kwargs) -> None:
        super().__init__(name="Reviewer", **kwargs)

    def review(
        self,
        language: Language,
        problem_statement: str,
        code: str,
    ) -> Tuple[str, List[str]]:
        """Review the candidate code and return a corrected version.

        Args:
            language: Target programming language.
            problem_statement: The original problem description.
            code: The candidate code produced by the coder agent.

        Returns:
            A ``(final_code, review_notes)`` tuple. If review fails the original
            code is returned with a note so the user still gets a usable result.

        Raises:
            AgentError: Only if the review response is structurally unusable and
                no fallback is possible.
        """
        user_prompt = (
            f"Target language: {language.display_name}\n"
            f"Problem statement:\n{problem_statement}\n\n"
            f"Candidate solution:\n{code}\n\n"
            "Review and return the improved solution as specified."
        )
        data = self._complete_json(_SYSTEM_PROMPT, user_prompt)
        final_code = str(data.get("code", "")).strip()
        notes_raw = data.get("review_notes", [])
        notes = (
            [str(n).strip() for n in notes_raw if str(n).strip()]
            if isinstance(notes_raw, list)
            else []
        )
        if not final_code:
            # Degrade gracefully: keep the coder's output rather than failing.
            return code, ["Reviewer returned no code; kept the original draft."]
        return final_code, notes
