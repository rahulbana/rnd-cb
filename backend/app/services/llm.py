"""Core LLM orchestration for the blog generator.

This module is where the "multi-step prompting / prompt chaining" happens:

    outline -> sections -> title -> meta description -> assembled article

Each function is a focused prompt. `generate_article` chains them together so a
single request produces a complete, coherent article.
"""

from __future__ import annotations

import json

from openai import OpenAI

from ..config import get_settings
from ..schemas import (
    LENGTH_SECTIONS,
    LENGTH_WORDS,
    ArticleLength,
    BlogBrief,
    OutlineItem,
    SectionResponse,
)


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns an unusable response."""


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError(
            "OPENAI_API_KEY is not set. Add it to backend/.env before generating."
        )
    return OpenAI(api_key=settings.openai_api_key)


def _chat(messages: list[dict], *, json_mode: bool = False, temperature: float = 0.7) -> str:
    settings = get_settings()
    kwargs: dict = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    client = _client()  # raises a clean LLMError if the API key is missing
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 - surface any SDK/HTTP error uniformly
        raise LLMError(f"OpenAI request failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise LLMError("OpenAI returned an empty response.")
    return content.strip()


def _brief_context(brief: BlogBrief) -> str:
    words = LENGTH_WORDS[brief.length]
    return (
        f"Topic: {brief.topic}\n"
        f"Target audience: {brief.audience}\n"
        f"Writing style: {brief.style}\n"
        f"Target length: {brief.length.value} (~{words} words total)"
    )


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Could not parse model JSON output: {exc}") from exc


# --------------------------------------------------------------------------- #
# Step 1: Outline
# --------------------------------------------------------------------------- #
def generate_outline(brief: BlogBrief) -> list[OutlineItem]:
    n_sections = LENGTH_SECTIONS[brief.length]
    system = (
        "You are an expert content strategist. You produce clear, logically "
        "ordered blog outlines tailored to a specific audience and style."
    )
    user = (
        f"{_brief_context(brief)}\n\n"
        f"Create an outline with an Introduction, about {n_sections} body "
        "sections, and a Conclusion. Return JSON of the form: "
        '{"outline": [{"heading": "...", "summary": "one sentence on what this '
        'section covers"}]}. Order the sections so the article flows naturally.'
    )
    raw = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_mode=True,
        temperature=0.6,
    )
    data = _parse_json(raw)
    items = data.get("outline", [])
    outline = [
        OutlineItem(heading=str(item.get("heading", "")).strip(),
                    summary=str(item.get("summary", "")).strip())
        for item in items
        if str(item.get("heading", "")).strip()
    ]
    if not outline:
        raise LLMError("The model did not return any outline sections.")
    return outline


# --------------------------------------------------------------------------- #
# Step 2: A single section
# --------------------------------------------------------------------------- #
def generate_section(
    brief: BlogBrief,
    heading: str,
    section_summary: str = "",
    outline: list[OutlineItem] | None = None,
) -> str:
    words = LENGTH_WORDS[brief.length]
    n_sections = max(LENGTH_SECTIONS[brief.length], 1)
    per_section = max(words // (n_sections + 2), 120)

    outline_context = ""
    if outline:
        headings = "\n".join(f"- {item.heading}" for item in outline)
        outline_context = f"\nFull article outline for context:\n{headings}\n"

    system = (
        "You are a skilled blog writer. You write one section at a time in "
        "Markdown, without repeating the section heading, and you keep a "
        "consistent voice across the whole article."
    )
    user = (
        f"{_brief_context(brief)}\n{outline_context}\n"
        f'Write the section titled "{heading}".\n'
        f"What it should cover: {section_summary or 'Use your best judgement.'}\n\n"
        f"Aim for roughly {per_section} words. Write in a {brief.style} style for "
        f"{brief.audience}. Do NOT include the heading itself in the output; "
        "return only the section body as Markdown."
    )
    return _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.75,
    )


# --------------------------------------------------------------------------- #
# Step 3: Title
# --------------------------------------------------------------------------- #
def generate_titles(brief: BlogBrief, count: int = 5) -> list[str]:
    system = "You are a copywriter who writes compelling, click-worthy blog titles."
    user = (
        f"{_brief_context(brief)}\n\n"
        f"Suggest {count} strong titles for this article. Return JSON: "
        '{"titles": ["...", "..."]}. Keep each title under 70 characters.'
    )
    raw = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_mode=True,
        temperature=0.85,
    )
    data = _parse_json(raw)
    titles = [str(t).strip() for t in data.get("titles", []) if str(t).strip()]
    if not titles:
        raise LLMError("The model did not return any titles.")
    return titles


# --------------------------------------------------------------------------- #
# Step 4: Meta description
# --------------------------------------------------------------------------- #
def generate_meta_description(brief: BlogBrief) -> str:
    system = "You are an SEO specialist who writes concise, compelling meta descriptions."
    user = (
        f"{_brief_context(brief)}\n\n"
        "Write a single SEO meta description of at most 155 characters that "
        "would make someone click. Return only the description text, no quotes."
    )
    text = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.6,
    )
    return text.strip().strip('"')


# --------------------------------------------------------------------------- #
# Step 5: Rewrite an existing section
# --------------------------------------------------------------------------- #
def rewrite_section(
    brief: BlogBrief, heading: str, content: str, instruction: str
) -> str:
    system = (
        "You are an editor who rewrites blog sections while preserving their "
        "meaning, returning polished Markdown."
    )
    user = (
        f"{_brief_context(brief)}\n\n"
        f'Section heading: "{heading}"\n'
        f"Rewrite instruction: {instruction}\n\n"
        "Existing section content:\n"
        f"---\n{content}\n---\n\n"
        "Return only the rewritten section body as Markdown, without the heading."
    )
    return _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.7,
    )


# --------------------------------------------------------------------------- #
# Orchestration: full article via prompt chaining
# --------------------------------------------------------------------------- #
def generate_article(brief: BlogBrief) -> dict:
    """Chain every step into one coherent article."""
    outline = generate_outline(brief)

    sections: list[SectionResponse] = []
    for item in outline:
        body = generate_section(brief, item.heading, item.summary, outline)
        sections.append(SectionResponse(heading=item.heading, content=body))

    titles = generate_titles(brief, count=3)
    title = titles[0]
    meta_description = generate_meta_description(brief)

    markdown = _assemble_markdown(title, sections)

    return {
        "title": title,
        "meta_description": meta_description,
        "outline": outline,
        "sections": sections,
        "markdown": markdown,
    }


def _assemble_markdown(title: str, sections: list[SectionResponse]) -> str:
    parts = [f"# {title}\n"]
    for section in sections:
        parts.append(f"## {section.heading}\n\n{section.content}\n")
    return "\n".join(parts).strip() + "\n"
