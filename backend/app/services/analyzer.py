"""LLM-powered resume analysis producing structured JSON output."""
import json

from openai import OpenAI, OpenAIError

from app.config import settings
from app.models import AnalysisResult

SYSTEM_PROMPT = """You are an expert technical recruiter and career coach. \
You analyze resumes and return a rigorous, honest, and constructive assessment. \
Base every judgement strictly on the resume text provided. Do not invent \
experience or skills that are not supported by the text. Return only JSON."""

# The JSON shape we ask the model to fill in. Kept in sync with AnalysisResult.
JSON_INSTRUCTIONS = """Analyze the resume and respond with a single JSON object \
matching exactly this schema (no markdown, no commentary):

{
  "overall_score": <integer 0-100, holistic quality of the resume>,
  "skills": [<technical and professional skills clearly present in the resume>],
  "missing_skills": [<relevant, in-demand skills for this candidate's field that
    are absent but would strengthen the resume>],
  "strengths": [<concrete strengths of this resume, 3-6 items>],
  "weaknesses": [<concrete weaknesses or gaps, 3-6 items>],
  "experience": {
    "total_years": <number, estimated total years of professional experience>,
    "seniority_level": <one of "Junior", "Mid", "Senior", "Lead", "Principal">,
    "summary": <2-3 sentence narrative of the candidate's experience>
  },
  "recommendations": [<specific, actionable improvements, 3-6 items ordered by
    impact>]
}

Scoring guidance: 90-100 outstanding, 75-89 strong, 60-74 solid with clear
improvements needed, 40-59 weak, below 40 poor. Be discerning; most resumes
score between 55 and 85."""

# Keep prompt size bounded regardless of resume length.
MAX_RESUME_CHARS = 15000


class AnalysisError(Exception):
    """Raised when the resume analysis cannot be completed."""


def _client() -> OpenAI:
    if not settings.llm_configured:
        raise AnalysisError(
            "OPENAI_API_KEY is not configured. Set it in backend/.env."
        )
    return OpenAI(api_key=settings.openai_api_key)


def analyze_resume(resume_text: str) -> AnalysisResult:
    """Send the resume text to the LLM and parse a structured result."""
    text = resume_text.strip()[:MAX_RESUME_CHARS]
    client = _client()

    user_prompt = f"{JSON_INSTRUCTIONS}\n\n--- RESUME START ---\n{text}\n--- RESUME END ---"

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except OpenAIError as exc:
        raise AnalysisError(f"LLM request failed: {exc}") from exc

    content = completion.choices[0].message.content or "{}"
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AnalysisError("LLM returned invalid JSON.") from exc

    try:
        # Pydantic validates and coerces; extra keys are ignored by default here.
        return AnalysisResult.model_validate(raw)
    except Exception as exc:
        raise AnalysisError(f"LLM response did not match schema: {exc}") from exc
