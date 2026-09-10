"""Deterministic grading for quiz mode / score calculation.

MCQ and True/False are graded by exact match. Short-answer is graded by
keyword overlap: the answer is counted correct when it mentions a sufficient
fraction of the expected keywords (a lightweight, transparent evaluation that
needs no extra LLM call).
"""
import re

from .schemas import (
    GradedItem,
    GradeRequest,
    GradeResponse,
    MCQQuestion,
    ShortAnswerQuestion,
    TrueFalseQuestion,
)

# Fraction of keywords that must appear for a short answer to count as correct.
_SHORT_ANSWER_THRESHOLD = 0.5


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def _tf_value(response: str) -> bool | None:
    r = response.strip().lower()
    if r in {"true", "t", "yes", "1"}:
        return True
    if r in {"false", "f", "no", "0"}:
        return False
    return None


def _grade_short_answer(q: ShortAnswerQuestion, response: str) -> bool:
    if not q.keywords:
        # Fall back to substring/exact-ish comparison when no keywords given.
        return _normalize(response) == _normalize(q.answer) or (
            len(response.strip()) > 0
            and _normalize(q.answer) in _normalize(response)
        )
    haystack = _normalize(response)
    hits = sum(1 for kw in q.keywords if _normalize(kw) in haystack)
    return hits / len(q.keywords) >= _SHORT_ANSWER_THRESHOLD


def grade(req: GradeRequest) -> GradeResponse:
    by_index = {a.index: a.response for a in req.answers}
    results: list[GradedItem] = []
    correct_count = 0

    for i, q in enumerate(req.questions):
        given = by_index.get(i, "")

        if isinstance(q, MCQQuestion):
            expected = q.answer
            is_correct = given.strip().upper() == expected
        elif isinstance(q, TrueFalseQuestion):
            expected = "true" if q.answer else "false"
            is_correct = _tf_value(given) is q.answer
        elif isinstance(q, ShortAnswerQuestion):
            expected = q.answer
            is_correct = _grade_short_answer(q, given)
        else:  # pragma: no cover - defensive
            expected = ""
            is_correct = False

        correct_count += int(is_correct)
        results.append(
            GradedItem(
                index=i,
                correct=is_correct,
                expected=str(expected),
                given=given,
                explanation=q.explanation,
            )
        )

    total = len(req.questions)
    score = round((correct_count / total) * 100, 1) if total else 0.0
    return GradeResponse(
        total=total,
        correct=correct_count,
        score_percent=score,
        results=results,
    )
