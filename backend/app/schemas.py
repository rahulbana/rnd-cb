"""Pydantic schemas for requests, responses, and structured LLM output.

These schemas double as the JSON-schema contract we hand to the LLM so it
returns strictly structured question data we can validate and grade.
"""
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionType(str, Enum):
    mcq = "mcq"
    true_false = "true_false"
    short_answer = "short_answer"


# --------------------------------------------------------------------------- #
# Structured question models (what the LLM must produce)
# --------------------------------------------------------------------------- #
class MCQOption(BaseModel):
    label: Literal["A", "B", "C", "D"]
    text: str


class MCQQuestion(BaseModel):
    type: Literal["mcq"] = "mcq"
    question: str
    options: list[MCQOption] = Field(min_length=4, max_length=4)
    answer: Literal["A", "B", "C", "D"] = Field(
        description="Label of the correct option"
    )
    explanation: str
    difficulty: Difficulty

    @field_validator("options")
    @classmethod
    def unique_labels(cls, v: list[MCQOption]) -> list[MCQOption]:
        labels = [o.label for o in v]
        if sorted(labels) != ["A", "B", "C", "D"]:
            raise ValueError("MCQ options must have exactly labels A, B, C, D")
        return v


class TrueFalseQuestion(BaseModel):
    type: Literal["true_false"] = "true_false"
    question: str
    answer: bool
    explanation: str
    difficulty: Difficulty


class ShortAnswerQuestion(BaseModel):
    type: Literal["short_answer"] = "short_answer"
    question: str
    answer: str = Field(description="Concise model answer")
    keywords: list[str] = Field(
        default_factory=list,
        description="Key terms an acceptable answer should contain",
    )
    explanation: str
    difficulty: Difficulty


Question = MCQQuestion | TrueFalseQuestion | ShortAnswerQuestion


class QuestionSet(BaseModel):
    """Top-level container the LLM returns."""
    questions: list[Question]


# --------------------------------------------------------------------------- #
# API request / response models
# --------------------------------------------------------------------------- #
class GenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=4000)
    difficulty: Difficulty = Difficulty.medium
    question_types: list[QuestionType] = Field(
        default_factory=lambda: [QuestionType.mcq]
    )
    num_questions: int = Field(default=5, ge=1, le=20)

    @field_validator("question_types")
    @classmethod
    def at_least_one(cls, v: list[QuestionType]) -> list[QuestionType]:
        if not v:
            raise ValueError("Select at least one question type")
        return v


class GenerateResponse(BaseModel):
    topic: str
    difficulty: Difficulty
    questions: list[Question]


# --------------------------------------------------------------------------- #
# Grading (quiz mode)
# --------------------------------------------------------------------------- #
class SubmittedAnswer(BaseModel):
    index: int = Field(ge=0, description="Index of the question in the set")
    response: str = Field(
        description="User's answer: option label, 'true'/'false', or free text"
    )


class GradeRequest(BaseModel):
    questions: list[Question]
    answers: list[SubmittedAnswer]


class GradedItem(BaseModel):
    index: int
    correct: bool
    expected: str
    given: str
    explanation: str


class GradeResponse(BaseModel):
    total: int
    correct: int
    score_percent: float
    results: list[GradedItem]
