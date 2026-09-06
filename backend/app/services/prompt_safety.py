"""Basic prompt-injection defenses for retrieved content.

Defense in depth: the system prompt tells the model the context is untrusted
data and the user template wraps it in <context> tags; this module additionally
neutralizes the most common injection phrasings inside retrieved text and flags
them for logging. It is deliberately conservative -- it redacts imperative
override phrases, not ordinary content.
"""

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+|the\s+)?(previous|above|prior)\s+instructions", re.I),
    re.compile(r"disregard\s+(all\s+|the\s+)?(previous|above|prior)", re.I),
    re.compile(r"forget\s+(everything|all\s+previous)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
]

_REDACTION = "[redacted]"


def detect_injection(text: str) -> bool:
    """Whether the text contains a known prompt-injection phrasing."""
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def sanitize_context(text: str) -> tuple[str, bool]:
    """Redact injection phrasings; return (clean_text, was_flagged)."""
    flagged = False
    clean = text
    for pattern in _INJECTION_PATTERNS:
        clean, n = pattern.subn(_REDACTION, clean)
        flagged = flagged or n > 0
    return clean, flagged
