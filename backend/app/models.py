"""Pydantic models for requests, responses, and the structured LLM output."""
from enum import Enum

from pydantic import BaseModel, Field


class WritingStyle(str, Enum):
    """Supported writing styles (tones) for generated copy."""

    professional = "professional"
    casual = "casual"
    luxury = "luxury"
    playful = "playful"
    technical = "technical"
    minimalist = "minimalist"


class DescriptionLength(str, Enum):
    """Controls verbosity of the detailed description."""

    short = "short"
    medium = "medium"
    long = "long"


# Sections that can be (re)generated individually.
SECTION_NAMES = [
    "title",
    "short_description",
    "detailed_description",
    "key_features",
    "benefits",
    "seo_keywords",
    "meta_description",
]


class ProductInput(BaseModel):
    """Product information supplied by the user."""

    product_name: str = Field(..., min_length=1, description="Name of the product.")
    features: list[str] = Field(default_factory=list, description="Raw feature bullet points.")
    category: str = Field("", description="Optional product category, e.g. 'Electronics'.")
    target_audience: str = Field("", description="Optional target audience for tailoring copy.")
    keywords: list[str] = Field(default_factory=list, description="Optional seed SEO keywords.")


class GenerationConfig(BaseModel):
    """Knobs that control the style and shape of the generated content."""

    style: WritingStyle = WritingStyle.professional
    length: DescriptionLength = DescriptionLength.medium
    num_variants: int = Field(1, ge=1, le=4, description="How many distinct variants to produce.")


class GenerateRequest(BaseModel):
    product: ProductInput
    config: GenerationConfig = Field(default_factory=GenerationConfig)


class RegenerateSectionRequest(BaseModel):
    product: ProductInput
    config: GenerationConfig = Field(default_factory=GenerationConfig)
    section: str = Field(..., description="Which section to regenerate.")


class ProductDescription(BaseModel):
    """The structured product description — this is the LLM's JSON schema target."""

    title: str = Field(..., description="Catchy, SEO-friendly product title.")
    short_description: str = Field(..., description="One or two punchy sentences.")
    detailed_description: str = Field(..., description="Rich paragraph-form description.")
    key_features: list[str] = Field(..., description="Bullet-point feature list.")
    benefits: list[str] = Field(..., description="Customer-facing benefit bullets.")
    seo_keywords: list[str] = Field(..., description="Relevant SEO keywords.")
    meta_description: str = Field(..., description="<=160 char SEO meta description.")


class GenerateResponse(BaseModel):
    variants: list[ProductDescription]


class RegenerateSectionResponse(BaseModel):
    section: str
    # Value is either a string or list[str] depending on the section.
    value: object
