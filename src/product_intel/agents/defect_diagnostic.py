"""Agent 4 - Problem & Defect Diagnostics.

Scans reviews for known defect patterns, deduplicates by canonical signature,
classifies each into the standardized taxonomy, and computes a frequency score +
severity weighting from review velocity and star ratings.
"""

from __future__ import annotations

from typing import Dict, List

from ..config import DEFAULT_WEIGHTS, DEFECT_PATTERNS, DefectPattern, ScoringWeights
from ..schemas import Defect, DefectCategory, DefectLog, IngestedProduct, Review

_CATEGORY_BY_VALUE = {c.value: c for c in DefectCategory}


class DefectDiagnosticAgent:
    def __init__(
        self,
        patterns: List[DefectPattern] = DEFECT_PATTERNS,
        weights: ScoringWeights = DEFAULT_WEIGHTS,
    ):
        self.patterns = patterns
        self.weights = weights

    def _matches(self, pattern: DefectPattern, text: str) -> bool:
        return any(kw in text for kw in pattern.keywords)

    def run(self, ingested: IngestedProduct) -> DefectLog:
        total = len(ingested.reviews) or 1
        # signature -> aggregation state
        hits: Dict[str, Dict] = {}

        for review in ingested.reviews:
            text = f"{review.title} {review.body}".lower()
            for pattern in self.patterns:
                if not self._matches(pattern, text):
                    continue
                state = hits.setdefault(
                    pattern.signature,
                    {"pattern": pattern, "reviews": [], "low_rating": 0},
                )
                state["reviews"].append(review)
                if review.rating and review.rating <= 3.0:
                    state["low_rating"] += 1

        defects: List[Defect] = []
        for i, (sig, state) in enumerate(hits.items()):
            pattern: DefectPattern = state["pattern"]
            reviews: List[Review] = state["reviews"]
            freq = len(reviews)
            freq_ratio = freq / total
            low_rating_ratio = state["low_rating"] / freq if freq else 0.0
            cat_weight = self.weights.category_weight.get(pattern.category, 0.5)
            severity = round(
                self.weights.severity_freq * min(1.0, freq_ratio * 3)
                + self.weights.severity_rating * low_rating_ratio
                + self.weights.severity_category * cat_weight,
                3,
            )
            defects.append(
                Defect(
                    defect_id=f"DEF-{i+1:03d}",
                    title=pattern.title,
                    category=_CATEGORY_BY_VALUE[pattern.category],
                    cluster=pattern.cluster,
                    frequency=freq,
                    frequency_ratio=round(freq_ratio, 4),
                    severity=severity,
                    representative_quotes=[_snippet(r) for r in reviews[:3]],
                )
            )

        defects.sort(key=lambda d: d.severity, reverse=True)
        # re-id after sorting so DEF-001 is the most severe
        for i, d in enumerate(defects):
            d.defect_id = f"DEF-{i+1:03d}"
        return DefectLog(defects=defects)


def _snippet(review: Review, limit: int = 160) -> str:
    text = review.body.strip() or review.title.strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text
