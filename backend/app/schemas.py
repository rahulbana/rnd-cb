"""Pydantic models describing the resume domain.

These schemas are used both as the request contract from the frontend and as
the structured-output target for the LLM. Keeping a single source of truth means
the JSON Schema we hand to OpenAI always matches what the API accepts.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class ResumeStyle(str, Enum):
    """Available visual templates for PDF rendering."""

    modern = "modern"
    classic = "classic"
    minimal = "minimal"
    creative = "creative"


class PersonalInfo(BaseModel):
    full_name: str = Field(..., description="Candidate's full name")
    title: Optional[str] = Field(
        None, description="Professional title, e.g. 'Senior Software Engineer'"
    )
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = Field(None, description="Portfolio or personal site URL")
    linkedin: Optional[str] = None
    github: Optional[str] = None


class Education(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = Field(None, description="e.g. 'Sep 2018'")
    end_date: Optional[str] = Field(None, description="e.g. 'Jun 2022' or 'Present'")
    gpa: Optional[str] = None
    details: List[str] = Field(
        default_factory=list, description="Notable coursework, honors, activities"
    )


class Experience(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = Field(None, description="'Present' if current role")
    highlights: List[str] = Field(
        default_factory=list,
        description="Achievement-oriented bullet points for this role",
    )


class Project(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    link: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    category: str = Field(..., description="e.g. 'Languages', 'Frameworks', 'Tools'")
    items: List[str] = Field(default_factory=list)


class ResumeInput(BaseModel):
    """Raw information supplied by the user through the form."""

    personal: PersonalInfo
    summary: Optional[str] = Field(
        None, description="Optional user-written professional summary"
    )
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    skills: List[str] = Field(
        default_factory=list, description="Flat list of skills the user typed"
    )
    projects: List[Project] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    target_role: Optional[str] = Field(
        None, description="Role the resume is being tailored towards"
    )


class GenerateRequest(BaseModel):
    """Payload for /api/generate."""

    input: ResumeInput
    style: ResumeStyle = ResumeStyle.modern
    tone: str = Field(
        "professional",
        description="Writing tone for AI copy, e.g. 'professional', 'concise', 'impactful'",
    )


class Resume(BaseModel):
    """The polished, structured resume produced by the LLM.

    This is the object that gets fed into a template to render a PDF.
    """

    personal: PersonalInfo
    summary: str = Field(..., description="Punchy 2-4 sentence professional summary")
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[SkillGroup] = Field(
        default_factory=list, description="Skills organized into sensible categories"
    )
    projects: List[Project] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    resume: Resume
    style: ResumeStyle


class RenderRequest(BaseModel):
    """Payload for /api/render-pdf: a (possibly user-edited) resume + style."""

    resume: Resume
    style: ResumeStyle = ResumeStyle.modern
