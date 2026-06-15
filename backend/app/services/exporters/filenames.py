"""Helpers for building download filenames from a plan."""
from __future__ import annotations

from app.schemas import StudyPlan


def plan_filename(plan: StudyPlan, ext: str) -> str:
    """A safe, descriptive filename like ``study-plan-math-quadratics.pdf``."""
    raw = f"study-plan-{plan.request.subject}-{plan.request.topic}".lower()
    slug = "".join(c if c.isalnum() else "-" for c in raw).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"{slug or 'study-plan'}.{ext}"
