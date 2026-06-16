"""Planner agent.

The planner turns a free-form problem statement into a concrete, ordered
implementation plan. Producing the plan first gives the coder agent a clear
specification to follow and makes the whole pipeline easier to debug.
"""
from __future__ import annotations

from typing import List

from app.agents.base import AgentError, BaseAgent
from app.schemas import Language

_SYSTEM_PROMPT = (
    "You are a senior software architect. Given a problem statement and a "
    "target programming language, you produce a concise, ordered implementation "
    "plan for a single, self-contained function or method that solves it.\n"
    "The plan must explicitly account for: input validation, edge cases, error "
    "and exception handling, and documentation.\n"
    "Respond ONLY with JSON of the form: {\"plan\": [\"step 1\", \"step 2\", ...]}. "
    "Each step is a short imperative sentence. Provide between 3 and 8 steps."
)


class PlannerAgent(BaseAgent):
    """Generates a step-by-step plan for the requested solution."""

    def __init__(self, **kwargs) -> None:
        super().__init__(name="Planner", **kwargs)

    def plan(self, language: Language, problem_statement: str) -> List[str]:
        """Create an ordered implementation plan.

        Args:
            language: Target programming language.
            problem_statement: The user's problem description.

        Returns:
            A list of plan steps.

        Raises:
            AgentError: If the model returns no usable plan.
        """
        user_prompt = (
            f"Target language: {language.display_name}\n"
            f"Problem statement:\n{problem_statement}\n\n"
            "Produce the implementation plan as specified."
        )
        data = self._complete_json(_SYSTEM_PROMPT, user_prompt)
        steps = data.get("plan")
        if not isinstance(steps, list) or not steps:
            raise AgentError("Planner did not return any plan steps.")
        # Coerce every step to a clean string and drop empties.
        cleaned = [str(step).strip() for step in steps if str(step).strip()]
        if not cleaned:
            raise AgentError("Planner returned an empty plan.")
        return cleaned
