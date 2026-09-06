"""Versioned Jinja2 prompt templates.

Prompts are versioned by filename (``rag_system.v1.jinja``) so a prompt change
is a new version, not an in-place edit -- the version is logged per request and
a bad answer can be traced to the exact prompt that produced it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

_PROMPTS_DIR = Path(__file__).parent


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_PROMPTS_DIR)),
        autoescape=select_autoescape(enabled_extensions=()),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


class PromptRenderer:
    """Renders the RAG system/user prompts for a given version."""

    def __init__(self, version: str = "v1") -> None:
        self.version = version

    def system(self, *, not_found_message: str) -> str:
        template = _env().get_template(f"rag_system.{self.version}.jinja")
        return template.render(not_found_message=not_found_message).strip()

    def user(self, *, question: str, context: str) -> str:
        template = _env().get_template(f"rag_user.{self.version}.jinja")
        return template.render(question=question, context=context).strip()
