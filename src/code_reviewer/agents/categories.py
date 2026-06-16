"""Definitions for each specialised review agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .base import ReviewAgent


@dataclass(frozen=True)
class AgentSpec:
    key: str
    category: str
    description: str
    checklist: List[str]


# Ordered roughly by priority — correctness first, as requested.
AGENT_SPECS: List[AgentSpec] = [
    AgentSpec(
        key="correctness",
        category="Correctness",
        description=(
            "The highest priority. Verify the code actually does what it "
            "claims and produces right results in all cases."
        ),
        checklist=[
            "Does the code do what it claims?",
            "Are edge cases handled?",
            "Are calculations correct?",
            "Are null/None values handled?",
            "Are exceptions handled properly?",
            "Could the code produce incorrect results?",
        ],
    ),
    AgentSpec(
        key="security",
        category="Security",
        description="Identify vulnerabilities and unsafe practices.",
        checklist=[
            "SQL Injection",
            "Command Injection",
            "Path Traversal",
            "Cross-Site Scripting (XSS)",
            "Hardcoded Secrets",
            "Unsafe Deserialization",
            "Authentication issues",
            "Authorization issues",
        ],
    ),
    AgentSpec(
        key="performance",
        category="Performance",
        description="Spot inefficiencies and scalability problems.",
        checklist=[
            "Nested loops",
            "Unnecessary database calls",
            "N+1 queries",
            "Large memory usage",
            "Inefficient algorithms",
        ],
    ),
    AgentSpec(
        key="readability",
        category="Readability",
        description="Assess how easy the code is to read and understand.",
        checklist=[
            "Variable naming",
            "Function naming",
            "Class naming",
            "Complexity",
            "Code organization",
        ],
    ),
    AgentSpec(
        key="maintainability",
        category="Maintainability",
        description="Assess how easy the code is to change and extend.",
        checklist=[
            "Duplicate code",
            "Long methods",
            "Large classes",
            "Tight coupling",
            "Magic numbers",
        ],
    ),
    AgentSpec(
        key="design",
        category="Design & Architecture",
        description="Evaluate the structural quality of the code.",
        checklist=[
            "SOLID principles",
            "Separation of concerns",
            "Dependency Injection",
            "Layered architecture",
            "Domain boundaries",
        ],
    ),
    AgentSpec(
        key="error_handling",
        category="Error Handling",
        description="Evaluate how failures are detected, surfaced, and recovered.",
        checklist=[
            "Are errors caught at the right level?",
            "Are exceptions swallowed silently?",
            "Are error messages clear and actionable?",
            "Are resources cleaned up on failure?",
            "Are failures logged appropriately?",
            "Are broad catch-all handlers misused?",
        ],
    ),
]

_SPEC_BY_KEY = {spec.key: spec for spec in AGENT_SPECS}


def default_category_keys() -> List[str]:
    return [spec.key for spec in AGENT_SPECS]


def build_agents(keys: List[str] | None = None) -> List[ReviewAgent]:
    """Instantiate agents for the given keys (or all, in priority order)."""
    selected = keys or default_category_keys()
    agents: List[ReviewAgent] = []
    for key in selected:
        spec = _SPEC_BY_KEY.get(key)
        if spec is None:
            valid = ", ".join(_SPEC_BY_KEY)
            raise ValueError(
                f"Unknown category '{key}'. Valid categories: {valid}"
            )
        agents.append(
            ReviewAgent(
                key=spec.key,
                category=spec.category,
                description=spec.description,
                checklist=spec.checklist,
            )
        )
    return agents
