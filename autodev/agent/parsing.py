"""Best-effort extraction of a JSON object from an LLM response.

Models occasionally wrap JSON in ``` fences or add stray prose despite
instructions. This finds and parses the first balanced JSON object.
"""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()

    # 1) Direct parse.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) Fenced code block.
    m = _FENCE.search(text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3) First balanced {...} span.
    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break

    raise ValueError("No valid JSON object found in model output")
