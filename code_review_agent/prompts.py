"""Prompt construction and the JSON schema handed to the model."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from .dependencies import Definition
from .reviewers.base import Reviewer

SYSTEM_PROMPT = (
    "You are a senior application security engineer and staff-level code "
    "reviewer. You review source code with rigor and precision. You never "
    "invent problems that are not present in the code. For every perspective "
    "you are asked about, you decide whether a genuine issue exists and, if "
    "so, you point to the exact lines and provide a concrete code fix that "
    "can be applied directly. When you propose a fix you ALWAYS include the "
    "exact existing code that must change (copied verbatim from the file) and "
    "the exact replacement or new code. You respond ONLY with the JSON object "
    "described by the user, and nothing else."
)


def build_response_schema(categories: List[Reviewer]) -> Dict[str, Any]:
    """Build a strict JSON schema so the model returns a predictable object."""

    issue_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "line",
            "end_line",
            "severity",
            "explanation",
            "current_code",
            "suggested_code",
        ],
        "properties": {
            "line": {
                "type": ["integer", "null"],
                "description": "1-based line where the issue starts (null if not applicable).",
            },
            "end_line": {
                "type": ["integer", "null"],
                "description": "1-based line where the issue ends (null if single line).",
            },
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
            },
            "explanation": {
                "type": "string",
                "description": "What is wrong at this location and why.",
            },
            "current_code": {
                "type": "string",
                "description": (
                    "The exact existing code that must change, copied verbatim "
                    "from the file (no line-number prefixes). Empty string if "
                    "this is purely new code to add."
                ),
            },
            "suggested_code": {
                "type": "string",
                "description": (
                    "The exact code to replace current_code with, or the exact "
                    "new code to add. Must be directly usable."
                ),
            },
        },
    }

    category_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "severity", "explanation", "suggestion", "issues"],
        "properties": {
            "status": {
                "type": "integer",
                "enum": [0, 1],
                "description": "1 if one or more issues were found, else 0.",
            },
            "severity": {
                "type": "string",
                "enum": ["none", "low", "medium", "high", "critical"],
                "description": "Worst severity across issues; 'none' when status is 0.",
            },
            "explanation": {
                "type": "string",
                "description": "Short summary of the category outcome.",
            },
            "suggestion": {
                "type": "string",
                "description": "Short summary of the recommended remediation.",
            },
            "issues": {
                "type": "array",
                "description": "Concrete issues with exact code fixes. Empty when status is 0.",
                "items": issue_schema,
            },
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [c.key for c in categories],
        "properties": {c.key: category_schema for c in categories},
    }


def number_lines(code: str) -> str:
    """Prefix each line with a 1-based number so the model can cite locations."""

    lines = code.splitlines()
    width = max(4, len(str(len(lines))))
    return "\n".join(f"{i:>{width}} | {line}" for i, line in enumerate(lines, start=1))


def build_dependency_block(dependencies: Sequence[Definition]) -> str:
    """Render resolved callee definitions as context for the reviewer."""

    if not dependencies:
        return (
            "DEPENDENCY DEFINITIONS: none resolved. Only flag call/usage errors "
            "that are evident from the code itself; do not speculate about "
            "functions whose definitions are not shown.\n\n"
        )

    parts = [
        "DEPENDENCY DEFINITIONS (definitions of functions/methods/classes this "
        "file calls, resolved from the project; use them to verify each call "
        "is consistent with its definition):\n"
    ]
    for d in dependencies:
        parts.append(
            f"# {d.kind} `{d.name}` from {d.file}:{d.start_line}\n"
            f"{d.snippet}\n---"
        )
    return "\n".join(parts) + "\n\n"


def build_manifest_block(manifests: Sequence[tuple]) -> str:
    """Render dependency-manifest files (requirements/pyproject) as context."""

    if not manifests:
        return ""
    parts = [
        "PROJECT DEPENDENCIES (declared dependency manifests; use them for the "
        "'dependency' perspective to compare declared vs imported packages, "
        "pinning and known issues):\n"
    ]
    for path, content in manifests:
        parts.append(f"# {path}\n{content}\n---")
    return "\n".join(parts) + "\n\n"


def build_user_prompt(
    *,
    file_path: str,
    language: str,
    code: str,
    categories: List[Reviewer],
    line_offset: int = 0,
    dependencies: Optional[Sequence[Definition]] = None,
    manifests: Optional[Sequence[tuple]] = None,
) -> str:
    """Compose the user message that carries the code and the instructions.

    ``line_offset`` shifts the displayed line numbers (used when reviewing a
    chunk of a larger file) so cited lines match the original file.
    ``dependencies`` are resolved callee definitions supplied as context.
    """

    perspective_lines = "\n".join(
        f'- "{c.key}" ({c.title}): {c.guidance}' for c in categories
    )
    keys = [c.key for c in categories]
    numbered = number_lines(code)
    if line_offset:
        # Re-number to reflect the file-absolute position of this chunk.
        numbered = _reoffset(code, line_offset)

    example = {
        keys[0]: {
            "status": 1,
            "severity": "critical",
            "explanation": "Short summary of the finding for this perspective.",
            "suggestion": "Short summary of how to fix it.",
            "issues": [
                {
                    "line": 12,
                    "end_line": 12,
                    "severity": "critical",
                    "explanation": "Concrete description of the problem on this line.",
                    "current_code": "os.system(cmd)",
                    "suggested_code": "subprocess.run(shlex.split(cmd), check=True)",
                }
            ],
        }
    }

    return (
        f"Review the following {language} code from `{file_path}`.\n"
        "The code is shown with `N | ` line-number prefixes for reference; "
        "those prefixes are NOT part of the code.\n\n"
        "Evaluate it independently for each of these perspectives:\n"
        f"{perspective_lines}\n\n"
        "Rules:\n"
        "- Set status = 1 only when there is a real, defensible issue; else 0.\n"
        "- When a perspective's guidance states an objective rule (e.g. uses "
        "MUST or calls something a 'definite issue'), apply it literally and "
        "report EVERY violation, even minor or stylistic ones — do not exempt "
        "code because it looks simple, short, or self-explanatory.\n"
        "- For every issue, populate `line` (and `end_line` for multi-line "
        "spans) with the numbers shown in the listing.\n"
        "- `current_code` MUST be the exact code from those lines, copied "
        "verbatim WITHOUT the `N | ` prefix. Use an empty string only when the "
        "fix is purely new code to add.\n"
        "- `suggested_code` MUST be the exact, directly-usable replacement or "
        "addition — real code, not a description.\n"
        "- When status = 0, use severity \"none\", a short explanation, an "
        "empty suggestion, and an empty `issues` array.\n"
        "- Do not speculate about code you cannot see.\n"
        "- Return a JSON object with exactly one key per perspective. Example "
        f"of a single entry:\n{json.dumps(example, indent=2)}\n\n"
        + build_dependency_block(dependencies or [])
        + build_manifest_block(manifests or [])
        + "CODE:\n"
        "```" + language + "\n"
        f"{numbered}\n"
        "```"
    )


def _reoffset(code: str, line_offset: int) -> str:
    lines = code.splitlines()
    last = line_offset + len(lines)
    width = max(4, len(str(last)))
    return "\n".join(
        f"{i:>{width}} | {line}"
        for i, line in enumerate(lines, start=line_offset + 1)
    )
