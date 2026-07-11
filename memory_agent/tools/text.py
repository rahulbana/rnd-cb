"""LLM-backed text tools: email drafting, summarizing, translating.

Each runs a focused, tool-free sub-call to the provided model so the main
conversation context stays clean.
"""

from __future__ import annotations

from langchain_core.tools import tool

from .base import run_llm_task


def make_text_tools(llm) -> list:
    @tool
    def draft_email(recipient: str, subject: str, key_points: str,
                    tone: str = "professional") -> str:
        """Draft an email from a recipient, subject, key points, and tone.

        `key_points` is a free-text description of what to say. Returns a ready
        subject line and body.
        """
        system = (
            "You are an expert email writer. Write a clear, well-structured "
            f"email in a {tone} tone. Return a 'Subject:' line followed by the "
            "body, with a greeting and sign-off. Do not add commentary."
        )
        user = f"Recipient: {recipient}\nSubject hint: {subject}\nKey points:\n{key_points}"
        return run_llm_task(llm, system, user)

    @tool
    def summarize_text(text: str, style: str = "concise") -> str:
        """Summarize a block of text. `style` e.g. 'concise', 'bullets', 'tl;dr'."""
        system = (
            f"Summarize the user's text in a {style} style. Preserve key facts, "
            "names, and numbers. Output only the summary."
        )
        return run_llm_task(llm, system, text)

    @tool
    def translate_text(text: str, target_language: str,
                       source_language: str = "auto") -> str:
        """Translate text into `target_language` (e.g. 'French', 'Hindi', 'ja')."""
        src = "" if source_language == "auto" else f" from {source_language}"
        system = (
            f"You are a professional translator. Translate the user's text{src} "
            f"into {target_language}. Preserve meaning, tone, and formatting. "
            "Output only the translation."
        )
        return run_llm_task(llm, system, text)

    return [draft_email, summarize_text, translate_text]
