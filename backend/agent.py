"""Resume-rating agent backed by the OpenAI API.

The agent takes a resume and a job description and returns a structured,
quantitative assessment of how well the candidate fits the role.
"""
from __future__ import annotations

import json
import os

from openai import OpenAI

from schemas import RateResponse

# Cap the amount of text we send to the model to keep latency/cost bounded.
MAX_CHARS = 20_000

SYSTEM_PROMPT = """You are an expert technical recruiter and hiring manager.
Your job is to objectively rate how well a candidate's resume matches a given
job description.

Evaluate the resume against the job description across these dimensions:
- Skills & Technologies: required and preferred skills present vs. missing.
- Experience: years and relevance of experience to the role.
- Education & Certifications: relevance of academic/professional credentials.
- Achievements & Impact: measurable results that signal seniority and ability.

Scoring rules:
- All scores are integers from 0 to 100.
- The overall_score should reflect a holistic fit, not a simple average.
- Be fair but rigorous. Do not inflate scores.
- Base every judgement ONLY on the provided resume and job description. Never
  invent experience the candidate does not list.

Return concise, specific, and actionable content."""

# JSON schema given to the model so it returns exactly the shape we need.
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overall_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "verdict": {"type": "string"},
        "summary": {"type": "string"},
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "reasoning": {"type": "string"},
                },
                "required": ["name", "score", "reasoning"],
            },
        },
        "matched_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overall_score",
        "verdict",
        "summary",
        "categories",
        "matched_skills",
        "missing_skills",
        "strengths",
        "gaps",
        "recommendations",
    ],
}


def _client() -> OpenAI:
    """Build an OpenAI client, raising a clear error if the key is missing."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add your key."
        )
    return OpenAI(api_key=api_key)


def rate_resume(resume: str, job_description: str) -> RateResponse:
    """Rate a resume against a job description and return a structured result."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = _client()

    user_prompt = (
        "Rate the following resume against the job description.\n\n"
        f"=== JOB DESCRIPTION ===\n{job_description[:MAX_CHARS]}\n\n"
        f"=== RESUME ===\n{resume[:MAX_CHARS]}\n"
    )

    completion = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "resume_rating",
                "strict": True,
                "schema": RESPONSE_SCHEMA,
            },
        },
    )

    raw = completion.choices[0].message.content or "{}"
    data = json.loads(raw)
    return RateResponse(**data)
