"""Structured output schema for the final, verified review report."""

from typing import List

from pydantic import BaseModel, Field


class Review(BaseModel):
    """A single customer review with its source so it can be verified/cited."""

    text: str = Field(..., description="The review text (quoted or faithfully summarized).")
    rating: str = Field(
        default="N/A",
        description="Star/score rating if available, e.g. '5/5', '1 star', or 'N/A'.",
    )
    source: str = Field(..., description="The source URL or platform the review came from.")


class ReviewReport(BaseModel):
    """The final verified report returned to the user."""

    subject: str = Field(..., description="What was researched (product / restaurant / hotel / etc.).")
    subject_type: str = Field(..., description="The category, e.g. 'restaurant', 'product', 'hotel'.")

    total_reviews_found: int = Field(
        ...,
        description="Approximate total number of reviewers/ratings found across all sources.",
    )

    overall_sentiment: str = Field(
        ...,
        description="One of: Positive, Mostly Positive, Mixed, Mostly Negative, Negative.",
    )
    sentiment_score: float = Field(
        ...,
        description="Overall positivity score from 0 (terrible) to 100 (excellent).",
    )
    conclusion: str = Field(
        ...,
        description="A clear, actionable verdict: should the user trust/visit/buy? Why?",
    )

    top_positive_reviews: List[Review] = Field(
        default_factory=list,
        description="Up to the 5 most representative POSITIVE reviews, each with its source.",
    )
    top_negative_reviews: List[Review] = Field(
        default_factory=list,
        description="Up to the 5 most representative NEGATIVE reviews, each with its source.",
    )

    authenticity_assessment: str = Field(
        ...,
        description=(
            "The verifier's judgement on how trustworthy the findings are: are the "
            "reviews genuine, are sources reputable, any signs of fake/paid reviews, "
            "and the confidence level (High/Medium/Low)."
        ),
    )

    sources: List[str] = Field(
        default_factory=list,
        description="All source URLs that back up this report.",
    )
