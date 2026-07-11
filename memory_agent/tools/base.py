"""Shared helpers for tool modules."""

from __future__ import annotations

from urllib.parse import urlparse

from langchain_core.messages import HumanMessage, SystemMessage

HTTP_TIMEOUT = 15


def run_llm_task(llm, system: str, user: str) -> str:
    """Run a one-shot, tool-free LLM sub-task and return its text.

    Used by the text tools (draft/summarize/translate) so they get a focused
    prompt without polluting the main conversation.
    """
    try:
        resp = llm.invoke([SystemMessage(system), HumanMessage(user)])
        return resp.content
    except Exception as exc:  # pragma: no cover - network dependent
        return f"(the language model call failed: {exc})"


def extract_host(domain_or_url: str) -> str:
    """Pull a bare hostname out of a domain or full URL."""
    s = domain_or_url.strip()
    if "//" not in s:
        s = "//" + s  # let urlparse treat the whole thing as a netloc
    return urlparse(s).hostname or domain_or_url.strip()
