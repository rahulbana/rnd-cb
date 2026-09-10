"""Supported languages and translation styles."""
from __future__ import annotations

# code -> human-readable name. "auto" means detect the source language.
LANGUAGES: dict[str, str] = {
    "auto": "Auto-detect",
    "en": "English",
    "hi": "Hindi",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "es": "Spanish",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "pt": "Portuguese",
    "ru": "Russian",
    "it": "Italian",
    "ko": "Korean",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "nl": "Dutch",
    "tr": "Turkish",
}

# Translation styles / tones and the instruction the model receives for each.
STYLES: dict[str, str] = {
    "formal": (
        "Use a formal, polite register. Prefer respectful pronouns and complete, "
        "professional phrasing suitable for business or official communication."
    ),
    "casual": (
        "Use a casual, friendly, conversational register as if talking to a friend. "
        "Contractions and everyday vocabulary are welcome."
    ),
    "technical": (
        "Preserve technical terminology, units, code, and domain-specific jargon. "
        "Keep the meaning precise and do not simplify technical concepts."
    ),
}

DEFAULT_STYLE = "formal"


def language_name(code: str) -> str:
    """Return the readable name for a language code, or the code itself."""
    return LANGUAGES.get(code, code)


def is_supported(code: str) -> bool:
    return code in LANGUAGES
