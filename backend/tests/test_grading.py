"""Tests for the deterministic grading logic (no OpenAI calls needed)."""
from app.grading import grade
from app.schemas import (
    Difficulty,
    GradeRequest,
    MCQOption,
    MCQQuestion,
    ShortAnswerQuestion,
    SubmittedAnswer,
    TrueFalseQuestion,
)


def _mcq() -> MCQQuestion:
    return MCQQuestion(
        question="What keyword defines a Python function?",
        options=[
            MCQOption(label="A", text="func"),
            MCQOption(label="B", text="def"),
            MCQOption(label="C", text="function"),
            MCQOption(label="D", text="lambda"),
        ],
        answer="B",
        explanation="Functions are defined with the 'def' keyword.",
        difficulty=Difficulty.easy,
    )


def _tf() -> TrueFalseQuestion:
    return TrueFalseQuestion(
        question="Python is dynamically typed.",
        answer=True,
        explanation="Types are checked at runtime.",
        difficulty=Difficulty.easy,
    )


def _short() -> ShortAnswerQuestion:
    return ShortAnswerQuestion(
        question="What does 'return' do in a function?",
        answer="It sends a value back to the caller and exits the function.",
        keywords=["value", "caller"],
        explanation="return passes a result back to the calling code.",
        difficulty=Difficulty.medium,
    )


def test_all_correct_scores_100():
    req = GradeRequest(
        questions=[_mcq(), _tf(), _short()],
        answers=[
            SubmittedAnswer(index=0, response="B"),
            SubmittedAnswer(index=1, response="true"),
            SubmittedAnswer(index=2, response="It returns a value to the caller"),
        ],
    )
    res = grade(req)
    assert res.total == 3
    assert res.correct == 3
    assert res.score_percent == 100.0


def test_mixed_scoring():
    req = GradeRequest(
        questions=[_mcq(), _tf()],
        answers=[
            SubmittedAnswer(index=0, response="a"),  # wrong (case-insensitive)
            SubmittedAnswer(index=1, response="false"),  # wrong
        ],
    )
    res = grade(req)
    assert res.correct == 0
    assert res.score_percent == 0.0


def test_mcq_case_insensitive():
    req = GradeRequest(
        questions=[_mcq()],
        answers=[SubmittedAnswer(index=0, response="b")],
    )
    assert grade(req).correct == 1


def test_short_answer_keyword_threshold():
    # Only one of two keywords -> exactly at 0.5 threshold -> correct.
    req = GradeRequest(
        questions=[_short()],
        answers=[SubmittedAnswer(index=0, response="it returns a value")],
    )
    assert grade(req).correct == 1

    # Zero keywords present -> incorrect.
    req2 = GradeRequest(
        questions=[_short()],
        answers=[SubmittedAnswer(index=0, response="no idea")],
    )
    assert grade(req2).correct == 0


def test_missing_answer_is_incorrect():
    req = GradeRequest(questions=[_mcq()], answers=[])
    res = grade(req)
    assert res.correct == 0
    assert res.results[0].given == ""
