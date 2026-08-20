"""OpenAI-backed generation of notes and questions from document text.

Questions are generated per type in separate, concurrent LLM calls. This keeps
each response well within output limits (so nothing is truncated) even when the
user asks for a large, exhaustive set of questions — ideal for thorough exam
preparation where every small concept should be covered.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from openai import OpenAI

from .schemas import (
    QUESTION_TYPES,
    CaseBasedQ,
    FillBlankQ,
    MCQ,
    NoteImage,
    NoteSection,
    Notes,
    Questions,
    ShortLongQ,
    StudyMaterial,
    TrueFalseQ,
)

# Model is configurable via env; default to a widely-available, capable model.
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Cap the amount of source text sent to the model to keep requests bounded.
MAX_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "48000"))

# Concurrency for the per-type question calls.
MAX_WORKERS = int(os.getenv("GENERATION_WORKERS", "6"))

# Safety ceiling so a single type can't request a runaway number of questions.
MAX_PER_TYPE = int(os.getenv("MAX_QUESTIONS_PER_TYPE", "40"))

# Detailed notes: how many sub-topics to expand, and how many to illustrate.
NOTES_MAX_SECTIONS = int(os.getenv("NOTES_MAX_SECTIONS", "14"))
NOTES_MAX_IMAGES = int(os.getenv("NOTES_MAX_IMAGES", "6"))


class LLMConfigError(Exception):
    """Raised when the OpenAI client cannot be configured."""


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMConfigError(
            "OPENAI_API_KEY is not set. Add it to the backend environment "
            "before generating study material."
        )
    return OpenAI(api_key=api_key)


# Target question counts per type at each coverage level. "exhaustive" is meant
# for serious exam prep — lots of questions covering even minor concepts.
COVERAGE_TARGETS: Dict[str, Dict[str, int]] = {
    "standard": {
        "true_false": 8, "mcq": 8, "fill_blanks": 6, "very_short": 6,
        "short": 5, "long": 3, "case_based": 2,
    },
    "thorough": {
        "true_false": 15, "mcq": 15, "fill_blanks": 12, "very_short": 12,
        "short": 8, "long": 5, "case_based": 3,
    },
    "exhaustive": {
        "true_false": 30, "mcq": 30, "fill_blanks": 24, "very_short": 24,
        "short": 16, "long": 10, "case_based": 6,
    },
}
DEFAULT_COVERAGE = os.getenv("DEFAULT_COVERAGE", "thorough")

# Per-type JSON shape (each object inside an "items" array) + a short guide.
_TYPE_SPECS = {
    "true_false": (
        '{"statement": "a factual statement", "answer": true or false, '
        '"explanation": "why it is true/false"}',
        "Mix true and false statements. Cover definitions, facts, and common "
        "misconceptions.",
    ),
    "mcq": (
        '{"question": "...", "options": ["first option text", "second option text", '
        '"third option text", "fourth option text"], '
        '"answer": "the exact text of the correct option", "explanation": "..."}',
        "Exactly 4 options each, with plausible distractors. Do NOT prefix "
        "options with letters or numbers like 'A.', 'B)', or '1.' — give the "
        "option text only. The answer must exactly match one option's text. Vary "
        "the correct option position.",
    ),
    "fill_blanks": (
        '{"question": "a sentence with a ______ blank", "answer": "the missing word/phrase"}',
        "Blank out key terms, names, dates, formulas, or values.",
    ),
    "very_short": (
        '{"question": "...", "answer": "a one-line answer"}',
        "One-mark style: definitions, one-word/one-line factual answers.",
    ),
    "short": (
        '{"question": "...", "answer": "a 2-3 sentence answer"}',
        "Short-answer style requiring brief explanation.",
    ),
    "long": (
        '{"question": "...", "answer": "a detailed, structured paragraph answer"}',
        "Long-answer/essay style covering a concept in depth.",
    ),
    "case_based": (
        '{"case": "a rich, detailed real-world scenario/passage (5-8 sentences) '
        'grounded in the material, with concrete context, data or examples", '
        '"questions": [{"question": "a higher-order sub-question", '
        '"answer": "a deep, well-explained answer (4-8 sentences) with reasoning, '
        'steps, and the underlying concept made explicit"}]}',
        "Each case must be an in-depth scenario/passage (at least 5 sentences) "
        "followed by 4-5 higher-order sub-questions that require analysis, "
        "application, and reasoning (not mere recall). Every answer must be "
        "thorough and clearly EXPLAINED in depth — state the reasoning, any "
        "steps/working, and the concept being tested — so a student fully "
        "understands why the answer is correct.",
    ),
}

_MODEL_BY_TYPE = {
    "true_false": TrueFalseQ,
    "mcq": MCQ,
    "fill_blanks": FillBlankQ,
    "very_short": ShortLongQ,
    "short": ShortLongQ,
    "long": ShortLongQ,
    "case_based": CaseBasedQ,
}


def _reference_block(research_context: str) -> str:
    if not research_context.strip():
        return ""
    return f"""

You may also use this ADDITIONAL REFERENCE MATERIAL gathered from reputable
educational sources online to add commonly-tested points and standard exam-style
patterns. The uploaded document is the primary source: prefer it, never
contradict it, and do not copy references verbatim.

=== ADDITIONAL REFERENCE MATERIAL START ===
{research_context.strip()}
=== ADDITIONAL REFERENCE MATERIAL END ==="""


def _audience(grade_level: str) -> str:
    return (
        f"The audience is a student at the {grade_level} level (and their parents)."
        if grade_level
        else "The audience is a student (and their parents)."
    )


def generate_study_material(
    text: str,
    selected_types: List[str],
    counts: Dict[str, int] | None = None,
    grade_level: str = "",
    research_context: str = "",
    coverage: str = "",
) -> StudyMaterial:
    """Generate notes and questions, one concurrent LLM call per question type."""
    selected_types = [t for t in selected_types if t in QUESTION_TYPES]
    if not selected_types:
        selected_types = list(QUESTION_TYPES)

    coverage = (coverage or DEFAULT_COVERAGE).lower()
    targets = COVERAGE_TARGETS.get(coverage, COVERAGE_TARGETS["thorough"])
    counts = counts or {}

    text = text[:MAX_CHARS]
    client = _client()
    ref_block = _reference_block(research_context)
    audience = _audience(grade_level)

    # Notes + each question type run concurrently.
    questions = Questions()
    with ThreadPoolExecutor(max_workers=max(1, MAX_WORKERS)) as ex:
        notes_future = ex.submit(
            _generate_detailed_notes, client, text, audience, ref_block
        )
        futures = {}
        for t in selected_types:
            n = min(int(counts.get(t, targets.get(t, 8))), MAX_PER_TYPE)
            futures[ex.submit(
                _generate_type, client, t, n, text, audience, ref_block
            )] = t

        try:
            notes = notes_future.result()
        except Exception:
            notes = Notes()

        for fut in as_completed(futures):
            t = futures[fut]
            try:
                setattr(questions, t, fut.result())
            except Exception:
                setattr(questions, t, [])

    return StudyMaterial(notes=notes, questions=questions)


def _generate_detailed_notes(
    client: OpenAI, text: str, audience: str, ref_block: str
) -> Notes:
    """Two-stage detailed notes: outline the sub-topics, then expand each deeply.

    Splitting per sub-topic keeps every section well within output limits, so the
    explanations can be long and detailed without truncation.
    """
    outline = _notes_outline(client, text, audience, ref_block)
    title = str(outline.get("title", "") or "")
    summary = str(outline.get("summary", "") or "")
    glossary = [str(g) for g in (outline.get("glossary") or []) if str(g).strip()]

    subs = []
    for s in (outline.get("subtopics") or [])[:NOTES_MAX_SECTIONS]:
        if isinstance(s, dict):
            heading = str(s.get("heading") or s.get("title") or "").strip()
            focus = str(s.get("focus") or s.get("hint") or "").strip()
        else:
            heading, focus = str(s).strip(), ""
        if heading:
            subs.append((heading, focus))

    # Expand each sub-topic into a detailed section, concurrently.
    sections: List[NoteSection | None] = [None] * len(subs)
    if subs:
        with ThreadPoolExecutor(max_workers=max(1, MAX_WORKERS)) as ex:
            futs = {
                ex.submit(
                    _generate_section, client, h, focus, text, audience, ref_block
                ): i
                for i, (h, focus) in enumerate(subs)
            }
            for fut in as_completed(futs):
                i = futs[fut]
                try:
                    sections[i] = fut.result()
                except Exception:
                    sections[i] = NoteSection(heading=subs[i][0])

    ordered = [s for s in sections if s is not None]
    _attach_images(ordered)
    return Notes(title=title, summary=summary, sections=ordered, glossary=glossary)


def _notes_outline(client: OpenAI, text: str, audience: str, ref_block: str) -> dict:
    prompt = f"""You are an expert teacher planning DETAILED study notes from the
document below. {audience}

Identify EVERY topic and sub-topic covered in the document, in the order they
appear. Be granular — split large topics into smaller sub-topics so each can be
studied on its own. Do not miss minor sub-topics.

Return ONLY valid JSON (no markdown fences) of this shape:
{{
  "title": "descriptive title of the whole document",
  "summary": "4-6 sentence overview of what the document covers",
  "subtopics": [
    {{"heading": "sub-topic name", "focus": "what this sub-topic should explain"}}
  ],
  "glossary": ["Term: short definition", "..."]
}}

=== DOCUMENT START ===
{text}
=== DOCUMENT END ==={ref_block}"""
    return _call_json(client, prompt)


def _generate_section(
    client: OpenAI, heading: str, focus: str, text: str, audience: str, ref_block: str
) -> NoteSection:
    focus_line = f"\nThis section should focus on: {focus}" if focus else ""
    prompt = f"""You are an expert teacher writing a DETAILED, well-explained study
note for ONE sub-topic. {audience}

Sub-topic: "{heading}".{focus_line}

Explain this sub-topic THOROUGHLY, as if teaching a student who wants to master
it: clear definitions, the underlying concepts and reasoning, how/why it works,
step-by-step where relevant, common mistakes, and worked examples. Write the
"explanation" as flowing prose in 2-4 short paragraphs (separate paragraphs with
a blank line). Base everything on the document (and reference material, if
given); do not invent unsupported facts.

Also suggest a helpful diagram/illustration to accompany the note via
"image_query" (a concise, specific search phrase), or "" if an image would not
help.

Return ONLY valid JSON (no markdown fences) of this shape:
{{
  "heading": "{heading}",
  "overview": "1-2 sentence introduction to the sub-topic",
  "explanation": "detailed multi-paragraph explanation",
  "key_points": ["important revision bullets, including small details"],
  "examples": ["worked example or illustration", "..."],
  "formulas": ["any formulas/equations with what each symbol means", "..."],
  "image_query": "concise image search phrase or empty string"
}}

=== DOCUMENT START ===
{text}
=== DOCUMENT END ==={ref_block}"""

    data = _call_json(client, prompt)
    image = None
    query = str(data.get("image_query", "") or "").strip()
    if query:
        image = NoteImage(query=query, caption=str(data.get("overview", "") or "")[:120])
    return NoteSection(
        heading=str(data.get("heading", heading) or heading),
        overview=str(data.get("overview", "") or ""),
        explanation=str(data.get("explanation", "") or ""),
        key_points=[str(p) for p in (data.get("key_points") or []) if str(p).strip()],
        examples=[str(p) for p in (data.get("examples") or []) if str(p).strip()],
        formulas=[str(p) for p in (data.get("formulas") or []) if str(p).strip()],
        image=image,
    )


def _attach_images(sections: List[NoteSection]) -> None:
    """Resolve online images for sections that requested one (best-effort)."""
    try:
        from .web_research import find_image, images_enabled
    except Exception:
        for s in sections:
            s.image = None
        return

    if not images_enabled():
        for s in sections:
            s.image = None
        return

    targets = [s for s in sections if s.image and s.image.query][:NOTES_MAX_IMAGES]
    if targets:
        with ThreadPoolExecutor(max_workers=min(4, len(targets))) as ex:
            futs = {ex.submit(find_image, s.image.query): s for s in targets}
            for fut in as_completed(futs):
                s = futs[fut]
                try:
                    info = fut.result()
                except Exception:
                    info = {}
                if info and info.get("url"):
                    s.image.url = info["url"]
                    s.image.source = info.get("source", "")
                    if not s.image.caption:
                        s.image.caption = info.get("title", "") or s.image.query
                else:
                    s.image = None

    # Drop unresolved image placeholders (beyond the cap or failed lookups).
    for s in sections:
        if s.image and not s.image.url:
            s.image = None


def _generate_type(
    client: OpenAI, qtype: str, n: int, text: str, audience: str, ref_block: str
) -> list:
    shape, guide = _TYPE_SPECS[qtype]
    prompt = f"""You are an expert exam-question writer. {audience}

From the document below, create {qtype.replace('_', ' ')} questions for exam
practice. {guide}

COVERAGE RULES (very important):
- Generate AT LEAST {n} questions.
- Test EVERY concept in the material, including small, minor, and easily
  overlooked facts — definitions, terms, names, dates, formulas, units,
  examples, exceptions, cause-and-effect, and comparisons.
- Make every question DISTINCT — do not repeat or trivially reword.
- Every question MUST include its correct answer so it can be self-checked.
- Base everything on the document (and reference material, if given); do not
  invent unsupported facts.

Return ONLY valid JSON (no markdown fences) of this shape:
{{"items": [{shape}, ... ]}}

=== DOCUMENT START ===
{text}
=== DOCUMENT END ==={ref_block}"""

    data = _call_json(client, prompt)
    items = data.get("items", []) if isinstance(data, dict) else []
    model = _MODEL_BY_TYPE[qtype]
    parsed = []
    for item in items:
        try:
            parsed.append(model.model_validate(item))
        except Exception:
            continue
    return parsed


def _call_json(client: OpenAI, prompt: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a meticulous educational content generator. You "
                    "always respond with a single valid JSON object and nothing "
                    "else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    return _safe_json(raw)


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        newline = raw.find("\n")
        if newline != -1:
            raw = raw[newline + 1:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
    return {}
