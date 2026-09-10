"""Lightweight source-language detection.

Uses Pygments' lexer guessing (no network, no LLM) with a few fast
heuristics layered on top for short snippets where Pygments is unreliable.
"""

from __future__ import annotations

import re

from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

# Map Pygments lexer names to friendly display names.
_NAME_NORMALISE = {
    "Python": "Python",
    "Python 2.x": "Python",
    "JavaScript": "JavaScript",
    "TypeScript": "TypeScript",
    "Java": "Java",
    "C": "C",
    "C++": "C++",
    "C#": "C#",
    "Go": "Go",
    "Rust": "Rust",
    "Ruby": "Ruby",
    "PHP": "PHP",
    "Swift": "Swift",
    "Kotlin": "Kotlin",
    "SQL": "SQL",
    "HTML": "HTML",
    "Bash": "Bash",
}

# Cheap, high-signal patterns checked before Pygments for tiny snippets.
_HEURISTICS: list[tuple[str, str]] = [
    (r"\bdef\s+\w+\s*\(.*\)\s*:", "Python"),
    (r"\b(import|from)\s+[\w.]+\s+import\b", "Python"),
    (r"\bfunction\s+\w+\s*\(", "JavaScript"),
    (r"\b(const|let|var)\s+\w+\s*=", "JavaScript"),
    (r"\binterface\s+\w+\s*\{", "TypeScript"),
    (r":\s*(string|number|boolean)\b", "TypeScript"),
    (r"\b(public|private|protected)\s+(static\s+)?(class|void|int)\b", "Java"),
    (r"#include\s*<\w+>", "C++"),
    (r"\bfn\s+\w+\s*\(", "Rust"),
    (r"\bfunc\s+\w+\s*\(", "Go"),
    (r"\bSELECT\b.+\bFROM\b", "SQL"),
]


def detect_language(code: str) -> str:
    """Return a best-effort language name, or 'Unknown'."""
    snippet = (code or "").strip()
    if not snippet:
        return "Unknown"

    for pattern, language in _HEURISTICS:
        if re.search(pattern, snippet, re.IGNORECASE | re.MULTILINE):
            return language

    try:
        lexer = guess_lexer(snippet)
    except ClassNotFound:
        return "Unknown"

    name = lexer.name
    return _NAME_NORMALISE.get(name, name)
