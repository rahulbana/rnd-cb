"""An offline LLM stub so the full agent loop can be tested without network.

It inspects the system prompt to decide which phase it's answering and returns
canned JSON that builds a tiny, genuinely-working Python project (stdlib only,
so no pip install is needed and tests pass on the first try).
"""
from __future__ import annotations

import json

from autodev.llm.base import LLMProvider

_PLAN = {
    "project_name": "adder",
    "language": "python",
    "description": "A tiny adder module with unittest tests.",
    "setup_commands": [],
    "test_command": "python -m unittest -v",
    "run_command": 'python -c "import adder; print(adder.add(2, 3))"',
    "files": [
        {"path": "adder.py", "purpose": "the add function"},
        {"path": "test_adder.py", "purpose": "unit tests"},
    ],
}

_FILES = {
    "files": [
        {
            "path": "adder.py",
            "content": "def add(a, b):\n    return a + b\n",
        },
        {
            "path": "test_adder.py",
            "content": (
                "import unittest\n"
                "from adder import add\n\n"
                "class TestAdd(unittest.TestCase):\n"
                "    def test_add(self):\n"
                "        self.assertEqual(add(2, 3), 5)\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            ),
        },
    ]
}


class StubProvider(LLMProvider):
    name = "stub"
    model = "stub-1"

    def __init__(self, broken_first: bool = False):
        # If broken_first, the first generate returns failing code to exercise
        # the fix loop.
        self.broken_first = broken_first
        self._generated = False

    async def chat(self, messages, temperature=0.2, on_token=None):
        system = messages[0]["content"] if messages else ""
        if "design and build complete" in system:
            payload = _PLAN
        elif "debugging your own project" in system:
            payload = _FILES  # correct code on fix
        else:
            # generator phase
            if self.broken_first and not self._generated:
                self._generated = True
                broken = json.loads(json.dumps(_FILES))
                broken["files"][0]["content"] = "def add(a, b):\n    return a - b\n"
                payload = broken
            else:
                payload = _FILES
        text = json.dumps(payload)
        if on_token:
            await on_token(text[:20])
        return text

    async def health(self) -> bool:
        return True
