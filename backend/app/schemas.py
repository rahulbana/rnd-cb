"""Pydantic schemas for requests and responses."""
from enum import Enum

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


class Emotion(str, Enum):
    joy = "joy"
    trust = "trust"
    anticipation = "anticipation"
    surprise = "surprise"
    sadness = "sadness"
    anger = "anger"
    fear = "fear"
    disgust = "disgust"
    neutral = "neutral"


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The text to analyze.")


class BatchAnalyzeRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="A list of texts to analyze.")


class Aspect(BaseModel):
    """A specific topic/aspect mentioned in the text and its polarity."""

    aspect: str = Field(..., description="Short label, e.g. 'Product quality'.")
    sentiment: Sentiment


class AnalysisResult(BaseModel):
    """The structured sentiment analysis of a single piece of text."""

    text: str = Field(..., description="The original input text.")
    overall: Sentiment = Field(..., description="Overall sentiment classification.")
    score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Sentiment score from -1 (very negative) to +1 (very positive).",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence from 0 to 1."
    )
    emotion: Emotion = Field(..., description="The dominant emotion.")
    emotion_scores: dict[str, float] = Field(
        default_factory=dict, description="Per-emotion intensity from 0 to 1."
    )
    positive_aspects: list[str] = Field(
        default_factory=list, description="Aspects mentioned positively."
    )
    negative_aspects: list[str] = Field(
        default_factory=list, description="Aspects mentioned negatively."
    )
    keywords: list[str] = Field(
        default_factory=list, description="Key terms extracted from the text."
    )
    summary: str = Field("", description="One-line summary of the sentiment.")


class BatchSummary(BaseModel):
    """Aggregate statistics across a batch of results."""

    total: int
    positive: int
    negative: int
    neutral: int
    mixed: int
    average_score: float
    average_confidence: float
    emotion_distribution: dict[str, int]
    top_positive_keywords: list[str]
    top_negative_keywords: list[str]


class BatchAnalysisResponse(BaseModel):
    results: list[AnalysisResult]
    summary: BatchSummary
