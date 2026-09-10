"""Pydantic models describing the resume analysis result."""
from pydantic import BaseModel, Field


class ExperienceAnalysis(BaseModel):
    total_years: float = Field(
        default=0,
        description="Estimated total years of professional experience.",
    )
    seniority_level: str = Field(
        default="",
        description="Estimated seniority, e.g. Junior, Mid, Senior, Lead.",
    )
    summary: str = Field(
        default="",
        description="A short narrative assessment of the candidate's experience.",
    )


class AnalysisResult(BaseModel):
    overall_score: int = Field(
        default=0, ge=0, le=100, description="Overall resume score from 0 to 100."
    )
    skills: list[str] = Field(
        default_factory=list, description="Skills detected in the resume."
    )
    missing_skills: list[str] = Field(
        default_factory=list,
        description="Relevant skills that appear to be missing.",
    )
    strengths: list[str] = Field(
        default_factory=list, description="Key strengths of the resume."
    )
    weaknesses: list[str] = Field(
        default_factory=list, description="Weaknesses or gaps in the resume."
    )
    experience: ExperienceAnalysis = Field(default_factory=ExperienceAnalysis)
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions to improve the resume.",
    )


class AnalyzeResponse(BaseModel):
    filename: str
    characters_extracted: int
    analysis: AnalysisResult
