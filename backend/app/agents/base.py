"""Shared agent primitives.

Each agent is a small, single-responsibility unit with a typed input and output.
Keeping them uniform makes the orchestrator trivial to read and each agent
independently testable.
"""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

I = TypeVar("I")  # noqa: E741  (input type)
O = TypeVar("O")  # noqa: E741  (output type)


class Agent(Protocol, Generic[I, O]):
    """Structural contract every agent satisfies."""

    name: str

    def run(self, payload: I) -> O:  # pragma: no cover - interface only
        ...


class AgentError(RuntimeError):
    """Base error for agent failures, carrying the agent name for context."""

    def __init__(self, agent: str, message: str) -> None:
        super().__init__(f"[{agent}] {message}")
        self.agent = agent
