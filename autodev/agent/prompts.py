"""Prompt templates for the autonomous build loop.

The agent uses a portable *structured-JSON* protocol rather than any single
vendor's function-calling format, so the exact same prompts work against both
OpenAI and Ollama models.
"""
from __future__ import annotations

import json

PLANNER_SYSTEM = """You are AutoDev, an autonomous senior software engineer.
You design and build complete, working software projects in ANY programming
language, entirely on your own. You are pragmatic and you always produce
runnable, testable code with automated tests.

Respond with a SINGLE valid JSON object and nothing else. No markdown code
fences, no prose before or after."""

GENERATOR_SYSTEM = """You are AutoDev, an autonomous senior software engineer.
You write complete, production-quality file contents. Never use placeholders
like "// ... rest of code" — always output the FULL content of every file.
Include automated tests. Respond with a SINGLE valid JSON object and nothing
else. No markdown code fences."""

FIXER_SYSTEM = """You are AutoDev, an autonomous senior software engineer
debugging your own project. You are given the plan, the current files, and the
failing command output. Diagnose the root cause and return corrected FULL file
contents for every file you need to change. Respond with a SINGLE valid JSON
object and nothing else."""


def plan_messages(goal: str, memory: list[str] | None = None) -> list[dict]:
    memory_block = ""
    if memory:
        joined = "\n- ".join(memory)
        memory_block = (
            "\nRelevant lessons from your past projects:\n- " + joined + "\n"
        )

    schema = {
        "project_name": "short-kebab-or-title name",
        "language": "primary language, e.g. python / javascript / go / rust",
        "description": "1-3 sentence description of what will be built",
        "setup_commands": [
            "shell commands to install dependencies, e.g. 'pip install -r requirements.txt'"
        ],
        "test_command": "single shell command that runs the automated tests",
        "run_command": "single shell command to run the app",
        "files": [
            {"path": "relative/path.ext", "purpose": "what this file is for"}
        ],
    }

    user = f"""Build this project autonomously:

\"\"\"{goal}\"\"\"
{memory_block}
Produce a concrete build plan as JSON with EXACTLY this shape:
{json.dumps(schema, indent=2)}

Rules:
- Choose the most appropriate language/stack for the request unless the request
  names one.
- Keep the project minimal but complete and genuinely runnable.
- ALWAYS include at least one automated test file and a working test_command.
- Prefer the language's standard tooling (pytest for python, node --test or
  jest for javascript, go test for go, etc.).
- List every file you will create in "files"."""
    return [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": user},
    ]


def generate_messages(goal: str, plan: dict) -> list[dict]:
    user = f"""Original request:
\"\"\"{goal}\"\"\"

Approved build plan:
{json.dumps(plan, indent=2)}

Now write the COMPLETE contents of every file in the plan. Return JSON:
{{
  "files": [
    {{"path": "relative/path.ext", "content": "FULL file content"}}
  ]
}}

Requirements:
- Output every file listed in the plan, plus any additional file the project
  needs to run (e.g. requirements.txt, package.json, go.mod, README.md).
- Code must be complete and self-consistent across files.
- Include real, meaningful automated tests that exercise the core behavior."""
    return [
        {"role": "system", "content": GENERATOR_SYSTEM},
        {"role": "user", "content": user},
    ]


def fix_messages(
    goal: str, plan: dict, files: dict[str, str], failing_output: str
) -> list[dict]:
    files_block = "\n\n".join(
        f"=== FILE: {path} ===\n{content}" for path, content in files.items()
    )
    # Guard against pathological context sizes.
    if len(files_block) > 60000:
        files_block = files_block[:60000] + "\n... [truncated] ..."
    failing_output = failing_output[-8000:]

    user = f"""Original request:
\"\"\"{goal}\"\"\"

Build plan:
{json.dumps(plan, indent=2)}

Current project files:
{files_block}

The command failed with this output:
--- OUTPUT START ---
{failing_output}
--- OUTPUT END ---

Fix the problem. Return JSON:
{{
  "explanation": "one sentence root-cause + fix",
  "files": [
    {{"path": "relative/path.ext", "content": "FULL corrected file content"}}
  ]
}}
Only include files that need to change, but give their FULL new content."""
    return [
        {"role": "system", "content": FIXER_SYSTEM},
        {"role": "user", "content": user},
    ]
