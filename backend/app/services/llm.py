"""LLM-backed structured resume generation.

The core idea (structured generation): we describe the exact JSON shape we want
via a Pydantic model and ask the model to fill it in. OpenAI's structured
outputs guarantee the response conforms to that schema, so we can parse it
straight back into typed objects.

If no API key is configured, `generate_resume` falls back to a deterministic
generator that assembles a reasonable resume locally. This keeps the whole
pipeline (form -> structured resume -> template -> PDF) working out of the box.
"""

from __future__ import annotations

import json
from typing import List

from ..config import get_settings
from ..schemas import (
    Education,
    Experience,
    PersonalInfo,
    Project,
    Resume,
    ResumeInput,
    SkillGroup,
)

SYSTEM_PROMPT = """\
You are an expert resume writer and career coach. You transform a candidate's
raw information into a polished, achievement-oriented resume.

Rules:
- Write in a {tone} tone. Never invent facts, employers, dates, or metrics that
  were not provided; you may rephrase and sharpen what the user gave you.
- Rewrite experience and project bullet points to be concise and impactful,
  ideally starting with a strong action verb and quantifying impact when the
  user supplied numbers.
- Produce a compelling 2-4 sentence professional summary. If the user provided
  one, refine it; otherwise synthesize it from their experience and skills.
- Group the user's flat list of skills into sensible categories (e.g.
  Languages, Frameworks, Tools, Cloud). Keep every skill the user provided.
- Preserve all education entries, employers, project names, and achievements.
- If a target role is given, subtly tailor emphasis toward that role without
  fabricating experience.
Return only the structured resume."""


def _build_user_prompt(data: ResumeInput) -> str:
    """Serialize the user's input into a compact prompt payload."""

    payload = data.model_dump(exclude_none=True)
    parts = [
        "Here is the candidate's information as JSON. Transform it into a "
        "polished structured resume following the rules.",
        "```json",
        json.dumps(payload, indent=2, default=str),
        "```",
    ]
    if data.target_role:
        parts.append(f"Tailor the resume toward this target role: {data.target_role}.")
    return "\n".join(parts)


def generate_resume(data: ResumeInput, tone: str = "professional") -> Resume:
    """Produce a polished `Resume` from raw `ResumeInput`.

    Uses OpenAI structured outputs when a key is available; otherwise falls back
    to a local deterministic assembler.
    """

    settings = get_settings()
    if not settings.llm_enabled:
        return _fallback_resume(data)

    # Imported lazily so the app can boot (and the fallback path can run)
    # without the openai package fully configured.
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(tone=tone)},
                {"role": "user", "content": _build_user_prompt(data)},
            ],
            response_format=Resume,
            temperature=0.4,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Model returned no parsed content")
        # Guarantee personal info is never lost by the model.
        parsed.personal = data.personal
        return parsed
    except Exception as exc:  # noqa: BLE001 - degrade gracefully to local build
        # Any API/parse failure should not take the product down; log and fall back.
        print(f"[llm] structured generation failed, using fallback: {exc}")
        return _fallback_resume(data)


# --------------------------------------------------------------------------- #
# Deterministic fallback (no LLM required)
# --------------------------------------------------------------------------- #

_SKILL_BUCKETS = {
    "Languages": {
        "python", "javascript", "typescript", "java", "c", "c++", "c#", "go",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "sql", "r", "bash",
    },
    "Frameworks & Libraries": {
        "react", "vue", "angular", "next.js", "nextjs", "svelte", "fastapi",
        "flask", "django", "express", "spring", "rails", "node.js", "nodejs",
        "pytorch", "tensorflow", "pandas", "numpy", "tailwind",
    },
    "Cloud & DevOps": {
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd",
        "jenkins", "github actions", "linux", "nginx",
    },
    "Databases": {
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite",
        "elasticsearch", "dynamodb",
    },
    "Tools": {"git", "jira", "figma", "vscode", "postman", "kafka", "rabbitmq"},
}


def _categorize_skills(skills: List[str]) -> List[SkillGroup]:
    groups: dict[str, List[str]] = {}
    other: List[str] = []
    for skill in skills:
        placed = False
        for category, members in _SKILL_BUCKETS.items():
            if skill.strip().lower() in members:
                groups.setdefault(category, []).append(skill.strip())
                placed = True
                break
        if not placed:
            other.append(skill.strip())
    result = [SkillGroup(category=c, items=v) for c, v in groups.items()]
    if other:
        result.append(SkillGroup(category="Other", items=other))
    return result


def _fallback_summary(data: ResumeInput) -> str:
    if data.summary:
        return data.summary
    title = data.personal.title or (data.target_role or "professional")
    years = len(data.experience)
    top_skills = ", ".join(data.skills[:4]) if data.skills else "a range of technologies"
    lead = f"{title} " if title else ""
    exp_clause = (
        f"with experience across {years} role{'s' if years != 1 else ''} "
        if years
        else ""
    )
    return (
        f"{lead}{exp_clause}skilled in {top_skills}. "
        "Focused on delivering reliable, well-crafted solutions and "
        "collaborating effectively across teams."
    ).strip()


def _fallback_resume(data: ResumeInput) -> Resume:
    """Assemble a resume locally without calling any model."""

    experience = [
        Experience(
            **{
                **exp.model_dump(),
                "highlights": exp.highlights
                or ([f"Contributed to key initiatives at {exp.company}."]),
            }
        )
        for exp in data.experience
    ]
    projects = [
        Project(
            **{
                **proj.model_dump(),
                "highlights": proj.highlights
                or ([proj.description] if proj.description else []),
            }
        )
        for proj in data.projects
    ]

    return Resume(
        personal=data.personal,
        summary=_fallback_summary(data),
        experience=experience,
        education=list(data.education),
        skills=_categorize_skills(data.skills),
        projects=projects,
        achievements=list(data.achievements),
    )
