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
        notes_future = ex.submit(_generate_notes, client, text, audience, ref_block)
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


def _generate_notes(client: OpenAI, text: str, audience: str, ref_block: str) -> Notes:
    prompt = f"""You are an expert teacher preparing thorough revision NOTES from
the document below. {audience}

Make the notes COMPREHENSIVE and GRANULAR — capture every concept, including
minor and easily-overlooked details: definitions, key terms, names, dates,
formulas, units, examples, and exceptions. Organise by sub-topic. Keep language
age-appropriate. Base the notes on the document (and reference material, if
given); do not invent unsupported facts.

Return ONLY valid JSON (no markdown fences) of this shape:
{{
  "title": "short descriptive title",
  "summary": "3-5 sentence overview",
  "key_points": ["many concise revision bullets covering all concepts"],
  "sections": [{{"heading": "sub-topic", "points": ["detailed point", "..."]}}],
  "glossary": ["Term: short definition", "..."]
}}

=== DOCUMENT START ===
{text}
=== DOCUMENT END ==={ref_block}"""

    data = _call_json(client, prompt)
    return Notes.model_validate(data)


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
