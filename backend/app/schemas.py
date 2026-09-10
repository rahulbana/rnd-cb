from enum import Enum

from pydantic import BaseModel, Field


class ArticleLength(str, Enum):
    short = "short"
    medium = "medium"
    long = "long"


# Approximate target word counts per length setting, used to steer the model.
LENGTH_WORDS: dict[ArticleLength, int] = {
    ArticleLength.short: 500,
    ArticleLength.medium: 1000,
    ArticleLength.long: 1800,
}

# Approximate number of body sections per length setting.
LENGTH_SECTIONS: dict[ArticleLength, int] = {
    ArticleLength.short: 3,
    ArticleLength.medium: 5,
    ArticleLength.long: 7,
}


class BlogBrief(BaseModel):
    """The core inputs that describe the article the user wants."""

    topic: str = Field(..., min_length=1, description="Main subject of the article.")
    audience: str = Field(
        "a general audience",
        description="Who the article is written for.",
    )
    style: str = Field(
        "informative and engaging",
        description="Desired writing style / tone.",
    )
    length: ArticleLength = Field(
        ArticleLength.medium, description="Target article length."
    )


class OutlineItem(BaseModel):
    heading: str
    summary: str = ""


class OutlineRequest(BlogBrief):
    pass


class OutlineResponse(BaseModel):
    outline: list[OutlineItem]


class SectionRequest(BlogBrief):
    heading: str = Field(..., description="Heading of the section to write.")
    section_summary: str = Field(
        "", description="Short summary of what the section should cover."
    )
    outline: list[OutlineItem] = Field(
        default_factory=list,
        description="Full outline for context so sections stay coherent.",
    )


class SectionResponse(BaseModel):
    heading: str
    content: str


class ArticleRequest(BlogBrief):
    pass


class ArticleResponse(BaseModel):
    title: str
    meta_description: str
    outline: list[OutlineItem]
    sections: list[SectionResponse]
    markdown: str


class TitleRequest(BlogBrief):
    pass


class TitleResponse(BaseModel):
    titles: list[str]


class MetaDescriptionRequest(BlogBrief):
    pass


class MetaDescriptionResponse(BaseModel):
    meta_description: str


class RewriteRequest(BlogBrief):
    heading: str = Field(..., description="Heading of the section being rewritten.")
    content: str = Field(..., description="Existing section content to rewrite.")
    instruction: str = Field(
        "Improve clarity and flow.",
        description="How the section should be rewritten.",
    )


class RewriteResponse(BaseModel):
    heading: str
    content: str
