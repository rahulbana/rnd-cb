"""Language translation backed by the free Google Translate web endpoint.

This is a *native application tool* (not sourced from the remote MCP server). It
uses :mod:`deep_translator`, which requires no API key, and runs the blocking
translate call in a worker thread so it never stalls the async event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    InvalidSourceOrTargetLanguage,
    LanguageNotSupportedException,
    TranslationNotFound,
)


class TranslationError(RuntimeError):
    """Raised when a translation cannot be produced."""


def _supported() -> dict[str, str]:
    # Maps human-readable names -> ISO codes, e.g. {"spanish": "es", ...}
    return GoogleTranslator().get_supported_languages(as_dict=True)


def _normalise_language(value: str, *, allow_auto: bool) -> str:
    token = value.strip().lower()
    if allow_auto and token in {"auto", "detect", "automatic"}:
        return "auto"
    supported = _supported()
    if token in supported:  # full name -> code
        return supported[token]
    if token in supported.values():  # already an ISO code
        return token
    raise TranslationError(
        f"Unsupported language '{value}'. Use an ISO code (e.g. 'es') or a "
        f"language name (e.g. 'spanish')."
    )


async def translate_text(
    text: str,
    target_language: str,
    source_language: str = "auto",
) -> dict[str, Any]:
    """Translate ``text`` into ``target_language``.

    ``source_language`` defaults to automatic detection.
    """
    if not text or not text.strip():
        raise TranslationError("No text was provided to translate.")

    target = _normalise_language(target_language, allow_auto=False)
    source = _normalise_language(source_language, allow_auto=True)

    def _run() -> str:
        return GoogleTranslator(source=source, target=target).translate(text)

    try:
        translated = await asyncio.to_thread(_run)
    except (
        LanguageNotSupportedException,
        InvalidSourceOrTargetLanguage,
        TranslationNotFound,
    ) as exc:
        raise TranslationError(f"Translation failed: {exc}") from exc

    return {
        "source_language": source,
        "target_language": target,
        "original_text": text,
        "translated_text": translated,
    }


def list_languages() -> dict[str, str]:
    """Return the supported ``name -> ISO code`` mapping."""
    return _supported()
