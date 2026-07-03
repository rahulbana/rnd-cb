"""Prompt construction and the JSON schema handed to the model."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .models import ReviewCategory

SYSTEM_PROMPT = (
    "You are a senior application security engineer and staff-level code "
    "reviewer. You review source code with rigor and precision. You never "
    "invent problems that are not present in the code. For every perspective "
    "you are asked about, you decide whether a genuine issue exists and, if "
    "so, explain it concretely (referencing the relevant construct) and give "
    "an actionable, specific suggestion to fix it. You respond ONLY with the "
    "JSON object described by the user, and nothing else."
)


def build_response_schema(categories: List[ReviewCategory]) -> Dict[str, Any]:
    """Build a strict JSON schema so the model returns a predictable object."""

    category_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "severity", "explanation", "suggestion"],
        "properties": {
            "status": {
                "type": "integer",
                "enum": [0, 1],
                "description": "1 if an issue was found for this category, else 0.",
            },
            "severity": {
                "type": "string",
                "enum": ["none", "low", "medium", "high", "critical"],
                "description": "Severity of the issue; 'none' when status is 0.",
            },
            "explanation": {
                "type": "string",
                "description": "Concise explanation of the issue, or why it is clean.",
            },
            "suggestion": {
                "type": "string",
                "description": "Actionable fix; empty string when status is 0.",
            },
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [c.key for c in categories],
        "properties": {c.key: category_schema for c in categories},
    }


def build_user_prompt(
    *,
    file_path: str,
    language: str,
    code: str,
    categories: List[ReviewCategory],
) -> str:
    """Compose the user message that carries the code and the instructions."""

    perspective_lines = "\n".join(
        f'- "{c.key}" ({c.title}): {c.guidance}' for c in categories
    )
    keys = [c.key for c in categories]
    example = {
        keys[0]: {
            "status": 1,
            "severity": "high",
            "explanation": "Concrete description of the problem.",
            "suggestion": "Specific, actionable remediation.",
        }
    }

    return (
        f"Review the following {language} code from `{file_path}`.\n\n"
        "Evaluate it independently for each of these perspectives:\n"
        f"{perspective_lines}\n\n"
        "Rules:\n"
        "- Set status = 1 only when there is a real, defensible issue for that "
        "perspective; otherwise set status = 0.\n"
        "- When status = 0, use severity \"none\", a short explanation stating "
        "it is clean, and an empty suggestion.\n"
        "- Keep explanations specific to this code (name the function, line, "
        "or construct). Do not speculate about code you cannot see.\n"
        "- Return a JSON object with exactly one key per perspective. Example "
        f"of a single entry:\n{json.dumps(example, indent=2)}\n\n"
        "CODE:\n"
        "```" + language + "\n"
        f"{code}\n"
        "```"
    )
