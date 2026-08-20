"""Pydantic models for request options and the generated study material."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# The question categories the user asked for. The values double as the keys the
# LLM is asked to return and the identifiers the frontend toggles.
QUESTION_TYPES = [
    "true_false",
    "mcq",
    "fill_blanks",
    "very_short",
    "short",
    "long",
    "case_based",
]

QUESTION_TYPE_LABELS = {
    "true_false": "True / False",
    "mcq": "Multiple Choice (MCQ)",
    "fill_blanks": "Fill in the Blanks",
    "very_short": "Very Short Answer",
    "short": "Short Answer",
    "long": "Long Answer",
    "case_based": "Case-Based",
}


class NoteSection(BaseModel):
    heading: str = ""
    points: List[str] = Field(default_factory=list)


class Notes(BaseModel):
    title: str = ""
    summary: str = ""
    key_points: List[str] = Field(default_factory=list)
    sections: List[NoteSection] = Field(default_factory=list)
    glossary: List[str] = Field(default_factory=list)


class TrueFalseQ(BaseModel):
    statement: str
    answer: bool
    explanation: str = ""


class MCQ(BaseModel):
    question: str
    options: List[str] = Field(default_factory=list)
    answer: str = ""  # the correct option text
    explanation: str = ""


class FillBlankQ(BaseModel):
    question: str
    answer: str = ""


class ShortLongQ(BaseModel):
    question: str
    answer: str = ""


class CaseQuestion(BaseModel):
    question: str
    answer: str = ""


class CaseBasedQ(BaseModel):
    case: str
    questions: List[CaseQuestion] = Field(default_factory=list)


class Questions(BaseModel):
    true_false: List[TrueFalseQ] = Field(default_factory=list)
    mcq: List[MCQ] = Field(default_factory=list)
    fill_blanks: List[FillBlankQ] = Field(default_factory=list)
    very_short: List[ShortLongQ] = Field(default_factory=list)
    short: List[ShortLongQ] = Field(default_factory=list)
    long: List[ShortLongQ] = Field(default_factory=list)
    case_based: List[CaseBasedQ] = Field(default_factory=list)


class StudyMaterial(BaseModel):
    notes: Notes = Field(default_factory=Notes)
    questions: Questions = Field(default_factory=Questions)


class Downloads(BaseModel):
    """Three self-contained, printable HTML documents."""

    notes: str = ""                    # study notes only
    questions_with_answers: str = ""   # questions + answer key
    questions_only: str = ""           # practice sheet, no answers


class GenerateResponse(BaseModel):
    source_filename: str
    grade_level: Optional[str] = None
    ocr_used: bool = False  # True when the source was read via OCR (scanned)
    web_search_used: bool = False  # True when online references were gathered
    sources: List[str] = Field(default_factory=list)  # reference URLs
    material: StudyMaterial
    downloads: Downloads
