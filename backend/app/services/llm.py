"""OpenAI-backed generation: summaries, Q&A and mind maps from a transcript."""
from __future__ import annotations

import re

from openai import OpenAI

from ..config import get_settings

# Rough char budget for the transcript we send to the model. gpt-4o-mini has a
# 128k-token context; ~60k characters (~15k tokens) keeps calls fast and cheap
# while covering most videos. Longer transcripts are trimmed with a marker.
_MAX_TRANSCRIPT_CHARS = 60_000


class LLMError(Exception):
    """Raised when the OpenAI call fails or is misconfigured."""


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError(
            "OPENAI_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    return OpenAI(api_key=settings.openai_api_key)


def _trim(transcript: str) -> str:
    if len(transcript) <= _MAX_TRANSCRIPT_CHARS:
        return transcript
    head = _MAX_TRANSCRIPT_CHARS * 2 // 3
    tail = _MAX_TRANSCRIPT_CHARS - head
    return (
        transcript[:head]
        + "\n\n[... transcript trimmed for length ...]\n\n"
        + transcript[-tail:]
    )


def _chat(system: str, user: str, *, temperature: float = 0.3) -> str:
    settings = get_settings()
    try:
        resp = _client().chat.completions.create(
            model=settings.openai_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"OpenAI request failed: {exc}") from exc

    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise LLMError("The model returned an empty response.")
    return content


def summarize(transcript: str, title: str | None = None) -> str:
    context = f'Video title: "{title}"\n\n' if title else ""
    system = (
        "You are a meticulous research assistant. You summarize YouTube video "
        "transcripts into clear, well-structured notes. Use Markdown. Be faithful "
        "to the transcript and never invent facts that aren't supported by it."
    )
    user = (
        f"{context}Summarize the following transcript.\n\n"
        "Structure the summary as:\n"
        "1. A one-sentence **TL;DR**.\n"
        "2. **Key Points** — a bullet list of the main ideas.\n"
        "3. **Takeaways** — 2-4 actionable or notable conclusions.\n\n"
        "Transcript:\n\"\"\"\n"
        f"{_trim(transcript)}\n\"\"\""
    )
    return _chat(system, user)


def answer_question(transcript: str, question: str, title: str | None = None) -> str:
    context = f'Video title: "{title}"\n\n' if title else ""
    system = (
        "You are a research assistant answering questions strictly about the "
        "content of a YouTube video, using its transcript as the only source. "
        "If the transcript does not contain the answer, say so plainly instead of "
        "guessing. Answer in Markdown and quote or reference the transcript where "
        "helpful."
    )
    user = (
        f"{context}Transcript:\n\"\"\"\n{_trim(transcript)}\n\"\"\"\n\n"
        f"Question: {question}"
    )
    return _chat(system, user)


def _sanitize_mermaid(text: str) -> str:
    """Strip code fences and ensure the output starts with `mindmap`."""
    cleaned = text.strip()
    fence = re.match(r"^```(?:mermaid)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    # Drop any accidental leading prose before the mindmap keyword.
    idx = cleaned.find("mindmap")
    if idx > 0:
        cleaned = cleaned[idx:]
    if not cleaned.startswith("mindmap"):
        cleaned = "mindmap\n" + cleaned
    return cleaned.strip()


def mind_map(transcript: str, title: str | None = None) -> str:
    root = title or "Video"
    system = (
        "You convert YouTube transcripts into a Mermaid `mindmap` diagram. "
        "Output ONLY valid Mermaid mindmap syntax and nothing else — no prose, "
        "no code fences."
    )
    user = (
        "Create a Mermaid mindmap that captures the structure of this video.\n\n"
        "Rules:\n"
        "- Start with the line `mindmap`.\n"
        f"- The root node is `root(({root}))`.\n"
        "- Use 2-space indentation to show hierarchy (3-4 levels deep).\n"
        "- Keep node labels short (a few words). Avoid characters that break "
        "Mermaid such as parentheses, colons, or quotes inside labels.\n"
        "- Cover the main themes and their sub-points.\n\n"
        "Transcript:\n\"\"\"\n"
        f"{_trim(transcript)}\n\"\"\""
    )
    return _sanitize_mermaid(_chat(system, user, temperature=0.2))
