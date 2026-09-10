"""Prompt construction for question generation."""
from .schemas import GenerateRequest, QuestionType

_TYPE_DESCRIPTIONS = {
    QuestionType.mcq: (
        "Multiple choice questions with exactly 4 options labeled A, B, C, D "
        "and exactly one correct answer."
    ),
    QuestionType.true_false: "True/False questions with a boolean answer.",
    QuestionType.short_answer: (
        "Short-answer questions with a concise model answer and a list of "
        "keywords that an acceptable answer should mention."
    ),
}

SYSTEM_PROMPT = (
    "You are an expert educational content creator. You generate high-quality "
    "study questions from provided material. Every question must be factually "
    "correct, unambiguous, and self-contained. Always include a clear "
    "explanation of why the answer is correct. Respond ONLY with data that "
    "matches the required JSON schema."
)


def build_user_prompt(req: GenerateRequest) -> str:
    type_lines = "\n".join(
        f"- {t.value}: {_TYPE_DESCRIPTIONS[t]}" for t in req.question_types
    )
    types_csv = ", ".join(t.value for t in req.question_types)

    return (
        f"Generate {req.num_questions} questions at '{req.difficulty.value}' "
        f"difficulty about the following topic/content.\n\n"
        f"TOPIC / CONTENT:\n{req.topic}\n\n"
        f"Allowed question types ({types_csv}) — distribute questions across "
        f"these types as evenly as possible:\n{type_lines}\n\n"
        f"Requirements:\n"
        f"- Set each question's 'difficulty' field to '{req.difficulty.value}'.\n"
        f"- Set each question's 'type' field to one of: {types_csv}.\n"
        f"- Ground every question strictly in the provided topic/content.\n"
        f"- Make distractors (wrong MCQ options) plausible but clearly incorrect.\n"
        f"- Keep explanations concise (1-3 sentences)."
    )
