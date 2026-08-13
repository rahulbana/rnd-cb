"""Prompt construction for test generation."""

from __future__ import annotations

from .languages import LanguageSpec

SYSTEM_PROMPT = (
    "You are a meticulous senior software engineer specializing in automated "
    "testing. You write thorough, idiomatic, runnable test suites. You cover "
    "the happy path, edge cases, boundary conditions, error handling, and "
    "invalid inputs. You use clear test names that describe the behavior under "
    "test. You never invent functions or symbols that don't exist in the "
    "source. You output ONLY the test file's contents with no explanation and "
    "no markdown code fences."
)


def build_user_prompt(
    *,
    spec: LanguageSpec,
    source_code: str,
    module_hint: str,
    description: str | None = None,
) -> str:
    """Assemble the user prompt for a single source file."""
    parts = [
        f"Write a complete test file for the following {spec.name} code using "
        f"{spec.framework}.",
        "",
        "Requirements:",
        f"- Use {spec.framework} idioms and assertions.",
        "- Import/reference the code under test from the module/path: "
        f"{module_hint}",
        "- Cover normal cases, edge cases, boundary values, and error paths.",
        "- Make tests independent and deterministic (no real network, no real "
        "filesystem, no wall-clock dependence); use mocks/stubs where needed.",
        "- Add brief comments only where a test's intent is non-obvious.",
        "- Output ONLY the raw file contents. No prose, no markdown fences.",
    ]
    if description:
        parts += ["", f"Additional context from the user: {description}"]
    parts += [
        "",
        "=== SOURCE CODE UNDER TEST ===",
        source_code,
        "=== END SOURCE CODE ===",
    ]
    return "\n".join(parts)
