"""Prompt templates and option vocabularies for the AI Email Writer.

Everything the model is told to do lives here so prompts stay easy to read,
tweak, and reason about. The API layer just fills these templates in.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Controlled vocabularies. The frontend renders these as dropdowns and the
# backend validates against them, so the two never drift apart.
# ---------------------------------------------------------------------------

EMAIL_TYPES: dict[str, str] = {
    "request": "a request asking someone to do or approve something",
    "follow_up": "a follow-up on a previous message or conversation",
    "introduction": "an introduction of yourself, a person, or a product",
    "thank_you": "a thank-you note expressing genuine appreciation",
    "apology": "an apology that takes responsibility and proposes a fix",
    "announcement": "an announcement sharing news or an update",
    "invitation": "an invitation to an event or meeting",
    "complaint": "a complaint raising an issue and requesting resolution",
    "sales_outreach": "a cold or warm sales outreach message",
    "general": "a general-purpose email",
}

TONES: dict[str, str] = {
    "professional": "polished, competent, and businesslike",
    "friendly": "warm, approachable, and personable",
    "formal": "respectful, precise, and traditionally structured",
    "casual": "relaxed and conversational, like writing to a peer",
    "persuasive": "confident and compelling, building a clear case",
    "empathetic": "understanding and considerate of the reader's feelings",
    "direct": "concise and to the point, no filler",
    "enthusiastic": "upbeat and energetic without being over the top",
}

# "Style" is a higher-level register that layers on top of tone.
STYLES: dict[str, str] = {
    "professional": "Keep it clean and business-appropriate.",
    "friendly": "Let some personality and warmth through.",
    "formal": "Use full sentences, honorifics where natural, and no contractions or slang.",
}

TRANSFORMS: dict[str, str] = {
    "shorten": "Make the email noticeably shorter and tighter while keeping every key point.",
    "expand": "Add helpful detail, context, and a little more warmth, without padding or repetition.",
}

# ---------------------------------------------------------------------------
# System prompt: the model's standing instructions for every request.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert email-writing assistant. You turn rough intent into "
    "clear, natural, well-structured emails that a real person would be happy "
    "to send. You never invent facts (names, dates, numbers, links) that the "
    "user did not provide; when a detail is missing, use a neutral placeholder "
    "in [square brackets]. You always reply with a single valid JSON object and "
    "nothing else."
)


def _describe(mapping: dict[str, str], key: str) -> str:
    """Return the human description for a key, falling back to the key itself."""
    return mapping.get(key, key.replace("_", " "))


def build_generate_prompt(
    intent: str,
    email_type: str,
    tone: str,
    style: str,
    recipient: str | None = None,
    sender: str | None = None,
) -> str:
    """Prompt for generating a brand-new email (subject + body) from intent."""
    recipient_line = (
        f"- Recipient: {recipient}\n" if recipient else "- Recipient: not specified\n"
    )
    sender_line = f"- Sender / sign-off name: {sender}\n" if sender else ""

    return (
        "Write an email based on the following brief.\n\n"
        f"- Intent: {intent}\n"
        f"- Email type: {_describe(EMAIL_TYPES, email_type)}\n"
        f"- Tone: {_describe(TONES, tone)}\n"
        f"- Style: {_describe(STYLES, style)}\n"
        f"{recipient_line}"
        f"{sender_line}"
        "\nRequirements:\n"
        "1. Write a clear, specific subject line (no 'Re:' prefix).\n"
        "2. Write a complete email body with a greeting, well-organized "
        "paragraphs, and a sign-off.\n"
        "3. Match the requested tone and style consistently.\n"
        "4. Keep it natural and human — no robotic filler or clichés.\n\n"
        'Respond with JSON shaped exactly as: {"subject": "...", "body": "..."}'
    )


def build_rewrite_prompt(
    body: str,
    tone: str,
    style: str,
    instruction: str | None = None,
) -> str:
    """Prompt for rewriting an existing email body."""
    extra = (
        f"\nAdditional instruction from the user: {instruction}\n" if instruction else ""
    )
    return (
        "Rewrite the email below so it reads better while preserving its "
        "meaning and all concrete details the writer included.\n\n"
        f"- Target tone: {_describe(TONES, tone)}\n"
        f"- Target style: {_describe(STYLES, style)}\n"
        f"{extra}"
        "\n--- ORIGINAL EMAIL ---\n"
        f"{body}\n"
        "--- END ORIGINAL EMAIL ---\n\n"
        "Keep or improve the subject if one is present. "
        'Respond with JSON shaped exactly as: {"subject": "...", "body": "..."} '
        "(use an empty string for subject if the original had none)."
    )


def build_transform_prompt(body: str, transform: str, subject: str | None = None) -> str:
    """Prompt for shortening or expanding an existing email body."""
    subject_line = f"Current subject: {subject}\n\n" if subject else ""
    return (
        f"{_describe(TRANSFORMS, transform)}\n\n"
        f"{subject_line}"
        "--- EMAIL ---\n"
        f"{body}\n"
        "--- END EMAIL ---\n\n"
        "Preserve the original tone, the greeting, and the sign-off. "
        'Respond with JSON shaped exactly as: {"subject": "...", "body": "..."}'
    )
