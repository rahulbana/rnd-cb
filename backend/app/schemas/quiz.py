"""Quiz question-bank schemas."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ShortQA(BaseModel):
    question: str
    answer: str


class MCQItem(BaseModel):
    question: str
    options: List[str] = Field(default_factory=list)
    answer: str = Field(..., description="The single correct option text.")


class MultiSelectItem(BaseModel):
    """MMCQ — multiple correct answers."""

    question: str
    options: List[str] = Field(default_factory=list)
    answers: List[str] = Field(
        default_factory=list, description="All correct option texts."
    )


class FillBlank(BaseModel):
    question: str = Field(..., description="A sentence containing a ____ blank.")
    answer: str


class TrueFalseItem(BaseModel):
    statement: str
    answer: bool


class CaseStudy(BaseModel):
    """A CBSE-style case/source-based question: a scenario plus sub-questions."""

    scenario: str = Field(..., description="A short real-world passage/scenario.")
    questions: List[ShortQA] = Field(
        default_factory=list, description="Sub-questions based on the scenario, with answers."
    )


class QuizOutput(BaseModel):
    short_questions: List[ShortQA] = Field(default_factory=list)
    mcqs: List[MCQItem] = Field(default_factory=list)
    multi_select_mcqs: List[MultiSelectItem] = Field(default_factory=list)
    fill_in_the_blanks: List[FillBlank] = Field(default_factory=list)
    true_false: List[TrueFalseItem] = Field(default_factory=list)
    case_studies: List[CaseStudy] = Field(default_factory=list)
    long_questions: List[ShortQA] = Field(default_factory=list)

    def total(self) -> int:
        """Total number of questions across all categories."""
        return (
            len(self.short_questions)
            + len(self.mcqs)
            + len(self.multi_select_mcqs)
            + len(self.fill_in_the_blanks)
            + len(self.true_false)
            + len(self.case_studies)
            + len(self.long_questions)
        )
