"""Coder agent.

The coder takes the planner's plan and writes the actual source code in the
requested language. The prompt strongly emphasises the qualities the user
asked for: validation, exception handling, and thorough documentation.
"""
from __future__ import annotations

from typing import List

from app.agents.base import AgentError, BaseAgent
from app.schemas import Language

_SYSTEM_PROMPT = (
    "You are an expert software engineer who writes clean, idiomatic, "
    "production-quality code in many languages.\n"
    "You will be given a target language, a problem statement, and an ordered "
    "implementation plan. Write a single, self-contained function or method "
    "(plus any small helpers it needs) that solves the problem.\n"
    "Hard requirements for the code you produce:\n"
    "  1. Validate all inputs and fail fast with clear messages on bad input.\n"
    "  2. Use the language's idiomatic exception/error handling around any "
    "operation that can fail.\n"
    "  3. Include thorough documentation: a doc-comment for the function "
    "(purpose, parameters, return value, errors raised) using the language's "
    "convention (docstrings, JSDoc, Javadoc, Doxygen, etc.).\n"
    "  4. Add a tiny runnable example or usage snippet as a comment.\n"
    "Respond ONLY with JSON of the form: "
    "{\"code\": \"<source code as a string>\", "
    "\"explanation\": \"<2-4 sentence plain-English explanation>\"}.\n"
    "Do NOT wrap the code in markdown fences inside the JSON string."
)


class CoderAgent(BaseAgent):
    """Writes the initial implementation from the plan."""

    def __init__(self, **kwargs) -> None:
        super().__init__(name="Coder", **kwargs)

    def write(
        self,
        language: Language,
        problem_statement: str,
        plan: List[str],
    ) -> tuple[str, str]:
        """Generate source code and an explanation.

        Args:
            language: Target programming language.
            problem_statement: The user's problem description.
            plan: The ordered plan produced by the planner agent.

        Returns:
            A ``(code, explanation)`` tuple.

        Raises:
            AgentError: If the model returns no code.
        """
        numbered_plan = "\n".join(f"{i}. {step}" for i, step in enumerate(plan, 1))
        user_prompt = (
            f"Target language: {language.display_name}\n"
            f"Problem statement:\n{problem_statement}\n\n"
            f"Implementation plan:\n{numbered_plan}\n\n"
            "Write the code now, following every hard requirement."
        )
        data = self._complete_json(_SYSTEM_PROMPT, user_prompt)
        code = str(data.get("code", "")).strip()
        explanation = str(data.get("explanation", "")).strip()
        if not code:
            raise AgentError("Coder did not return any code.")
        return code, explanation
