"""LLM-backed translation logic using the OpenAI API.

The module builds tightly-controlled prompts so the model behaves like a
translation engine (structured JSON output, style control, and language
detection) rather than a chat assistant.
"""
from __future__ import annotations

import json
from typing import Iterable

from openai import OpenAI

from .config import get_settings
from .languages import STYLES, language_name


class TranslationError(RuntimeError):
    """Raised when the model fails to return a usable translation."""


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise TranslationError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    kwargs: dict = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def _style_instruction(style: str) -> str:
    return STYLES.get(style, STYLES["formal"])


def _system_prompt(source_lang: str, target_lang: str, style: str) -> str:
    source_desc = (
        "Automatically detect the source language."
        if source_lang == "auto"
        else f"The source language is {language_name(source_lang)}."
    )
    return (
        "You are a professional translation engine. Translate the user's text "
        f"into {language_name(target_lang)}. {source_desc}\n"
        f"Style guidance: {_style_instruction(style)}\n"
        "Rules:\n"
        "- Translate meaning faithfully; do not add commentary or explanations.\n"
        "- Preserve formatting, line breaks, numbers, and named entities.\n"
        "- Do not answer questions in the text; only translate them.\n"
        "Respond ONLY with a JSON object of the form "
        '{"detected_source_lang": "<ISO 639-1 code>", "translation": "<translated text>"}.'
    )


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise TranslationError(f"Model returned invalid JSON: {content!r}") from exc


def translate_one(
    text: str,
    source_lang: str,
    target_lang: str,
    style: str,
) -> tuple[str, str]:
    """Translate a single text.

    Returns ``(translated_text, detected_source_lang)``.
    """
    client = _client()
    settings = get_settings()
    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _system_prompt(source_lang, target_lang, style)},
                {"role": "user", "content": text},
            ],
        )
    except Exception as exc:  # network / auth / rate-limit errors from SDK
        raise TranslationError(f"Translation request failed: {exc}") from exc

    content = completion.choices[0].message.content or ""
    data = _parse_json(content)
    translation = data.get("translation")
    if not isinstance(translation, str):
        raise TranslationError(f"Model response missing 'translation': {content!r}")
    detected = data.get("detected_source_lang") or (
        source_lang if source_lang != "auto" else "unknown"
    )
    return translation, str(detected)


def translate_batch(
    texts: Iterable[str],
    source_lang: str,
    target_lang: str,
    style: str,
) -> tuple[list[str], str]:
    """Translate multiple texts in a single request.

    Returns ``(translations, detected_source_lang)``. Order matches the input.
    """
    items = [t for t in texts]
    client = _client()
    settings = get_settings()

    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(items))
    system = (
        _system_prompt(source_lang, target_lang, style)
        .replace(
            'Respond ONLY with a JSON object of the form '
            '{"detected_source_lang": "<ISO 639-1 code>", "translation": "<translated text>"}.',
            "You will receive a numbered list of texts. Translate each item independently.\n"
            'Respond ONLY with a JSON object of the form '
            '{"detected_source_lang": "<ISO 639-1 code>", '
            '"translations": ["<item 1>", "<item 2>", ...]} '
            "where the translations array has exactly one entry per input item, in order.",
        )
    )

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": numbered},
            ],
        )
    except Exception as exc:
        raise TranslationError(f"Batch translation request failed: {exc}") from exc

    content = completion.choices[0].message.content or ""
    data = _parse_json(content)
    translations = data.get("translations")
    if not isinstance(translations, list) or len(translations) != len(items):
        raise TranslationError(
            f"Model returned {len(translations) if isinstance(translations, list) else 'no'} "
            f"translations for {len(items)} inputs: {content!r}"
        )
    detected = data.get("detected_source_lang") or (
        source_lang if source_lang != "auto" else "unknown"
    )
    return [str(t) for t in translations], str(detected)
