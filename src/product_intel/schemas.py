"""Typed data model shared across all agents in the pipeline.

These dataclasses are intentionally dependency-free (standard-library only) so
the whole system runs and is testable without installing anything. Every
structure exposes a ``to_dict`` for JSON serialization, and the final
:class:`ProductReviewReport` renders the exact output schema described in the
architecture plan (section 5).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Stage 1 - Web ingestion & normalization
# --------------------------------------------------------------------------- #
@dataclass
class Review:
    """A single normalized customer review."""

    review_id: str
    rating: float  # star rating, 1.0 - 5.0
    body: str
    title: str = ""
    timestamp: Optional[str] = None  # ISO-8601 date string
    verified_purchase: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductMetadata:
    """Canonical product facts scraped from the detail page."""

    product_id: str
    name: str
    manufacturer: str = ""
    price: Optional[float] = None
    currency: str = "USD"
    advertised_features: List[str] = field(default_factory=list)
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IngestedProduct:
    """Clean output of Agent 1: product metadata plus its review dataset."""

    metadata: ProductMetadata
    reviews: List[Review] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "reviews": [r.to_dict() for r in self.reviews],
        }


# --------------------------------------------------------------------------- #
# Stage 2 - Sentiment & topic clustering
# --------------------------------------------------------------------------- #
@dataclass
class ClusterSentiment:
    """A functional-dimension cluster with its aggregated sentiment."""

    name: str
    review_ids: List[str] = field(default_factory=list)
    mention_frequency: int = 0
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    sentiment_score: float = 0.0  # normalized 0.0 (all negative) - 1.0 (all positive)
    representative_quotes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SentimentReport:
    """Output of Agent 2."""

    total_reviews_analyzed: int
    filtered_out: int
    average_star_rating: float
    positive_sentiment_ratio: float
    clusters: List[ClusterSentiment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_reviews_analyzed": self.total_reviews_analyzed,
            "filtered_out": self.filtered_out,
            "average_star_rating": self.average_star_rating,
            "positive_sentiment_ratio": self.positive_sentiment_ratio,
            "clusters": [c.to_dict() for c in self.clusters],
        }


# --------------------------------------------------------------------------- #
# Stage 3a - Feature audit (good vs. bad)
# --------------------------------------------------------------------------- #
@dataclass
class CoreStrength:
    feature: str
    sentiment_score: float
    mention_frequency: int
    key_highlights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FeatureGap:
    feature: str
    sentiment_score: float
    gap_description: str
    mention_frequency: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FeatureAuditReport:
    """Output of Agent 3."""

    core_strengths: List[CoreStrength] = field(default_factory=list)
    feature_gaps: List[FeatureGap] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_strengths": [s.to_dict() for s in self.core_strengths],
            "feature_gaps": [g.to_dict() for g in self.feature_gaps],
        }


# --------------------------------------------------------------------------- #
# Stage 3b - Problem & defect diagnostics
# --------------------------------------------------------------------------- #
class DefectCategory(str, Enum):
    FUNCTIONAL_BLOCKER = "Functional Blocker"
    USABILITY_INCONVENIENCE = "Usability Inconvenience"
    AESTHETIC_COSMETIC = "Aesthetic/Cosmetic"


@dataclass
class Defect:
    defect_id: str
    title: str
    category: DefectCategory
    cluster: str
    frequency: int  # number of reviews mentioning it
    frequency_ratio: float  # share of all reviews
    severity: float  # 0.0 - 1.0 weighting from velocity + star ratings
    representative_quotes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d


@dataclass
class DefectLog:
    """Output of Agent 4."""

    defects: List[Defect] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"defects": [d.to_dict() for d in self.defects]}


# --------------------------------------------------------------------------- #
# Stage 4 - Roadmap & backlog synthesis
# --------------------------------------------------------------------------- #
class Priority(str, Enum):
    P0 = "P0"  # Must Fix
    P1 = "P1"  # High Impact
    P2 = "P2"  # Next Cycle


@dataclass
class RiceScore:
    reach: float
    impact: float
    confidence: float
    effort: float

    @property
    def score(self) -> float:
        if self.effort <= 0:
            return 0.0
        return round((self.reach * self.impact * self.confidence) / self.effort, 2)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["score"] = self.score
        return d


@dataclass
class BacklogItem:
    ticket_id: str
    type: str  # "Defect / Bug" or "Feature Enhancement"
    priority: Priority
    title: str
    frequency_impact: str
    proposed_action: str
    rice: Optional[RiceScore] = None
    user_story: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "ticket_id": self.ticket_id,
            "type": self.type,
            "priority": self.priority.value,
            "title": self.title,
            "frequency_impact": self.frequency_impact,
            "proposed_action": self.proposed_action,
            "user_story": self.user_story,
            "acceptance_criteria": list(self.acceptance_criteria),
        }
        if self.rice is not None:
            d["rice"] = self.rice.to_dict()
        return d


# --------------------------------------------------------------------------- #
# Final assembled report (section 5 output schema)
# --------------------------------------------------------------------------- #
@dataclass
class ProductReviewReport:
    product_summary: Dict[str, Any]
    core_strengths: List[CoreStrength]
    feature_gaps: List[FeatureGap]
    vnext_backlog: List[BacklogItem]
    clusters: List[ClusterSentiment] = field(default_factory=list)
    defects: List[Defect] = field(default_factory=list)
    generated_on: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self, *, include_diagnostics: bool = True) -> Dict[str, Any]:
        """Serialize to the plan's output schema.

        The top-level keys (``product_summary``, ``core_strengths``,
        ``feature_gaps``, ``vnext_backlog``) match section 5 of the
        architecture plan exactly. Cluster and defect diagnostics are appended
        under ``diagnostics`` for the dashboard and can be omitted for a strict
        issue-tracker payload.
        """

        out: Dict[str, Any] = {
            "product_summary": self.product_summary,
            "core_strengths": [s.to_dict() for s in self.core_strengths],
            "feature_gaps": [g.to_dict() for g in self.feature_gaps],
            "vnext_backlog": [b.to_dict() for b in self.vnext_backlog],
        }
        if include_diagnostics:
            out["diagnostics"] = {
                "generated_on": self.generated_on,
                "clusters": [c.to_dict() for c in self.clusters],
                "defects": [d.to_dict() for d in self.defects],
            }
        return out
