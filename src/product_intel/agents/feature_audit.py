"""Agent 3 - Feature Audit (good vs. bad).

Cross-examines each advertised marketing feature against the real per-cluster
sentiment from Agent 2. High-sentiment matches become *core differentiators*;
low-sentiment matches become *expectation mismatches* (feature gaps).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ..config import FEATURE_TO_CLUSTER_HINTS
from ..llm.base import LLMClient
from ..schemas import (
    ClusterSentiment,
    CoreStrength,
    FeatureAuditReport,
    FeatureGap,
    ProductMetadata,
    SentimentReport,
)


class FeatureAuditAgent:
    def __init__(
        self,
        llm: LLMClient,
        feature_hints: Dict[str, str] = FEATURE_TO_CLUSTER_HINTS,
        strength_threshold: float = 0.62,
        gap_threshold: float = 0.5,
    ):
        self.llm = llm
        self.feature_hints = feature_hints
        self.strength_threshold = strength_threshold
        self.gap_threshold = gap_threshold

    def _match_cluster(
        self, feature: str, clusters: Dict[str, ClusterSentiment]
    ) -> Optional[ClusterSentiment]:
        f = feature.lower()
        for hint, cluster_name in self.feature_hints.items():
            if hint in f and cluster_name in clusters:
                return clusters[cluster_name]
        # fallback: direct name overlap with a cluster label
        for name, cluster in clusters.items():
            if any(word in f for word in name.lower().split()):
                return cluster
        return None

    def run(
        self, metadata: ProductMetadata, sentiment: SentimentReport
    ) -> FeatureAuditReport:
        clusters = {c.name: c for c in sentiment.clusters}
        strengths: List[CoreStrength] = []
        gaps: List[FeatureGap] = []

        for feature in metadata.advertised_features:
            cluster = self._match_cluster(feature, clusters)
            if cluster is None:
                # Advertised but never discussed by users -> unvalidated promise.
                gaps.append(
                    FeatureGap(
                        feature=feature,
                        sentiment_score=0.0,
                        gap_description=(
                            f"Advertised feature '{feature}' is not mentioned in "
                            f"reviews - unvalidated by real usage."
                        ),
                        mention_frequency=0,
                    )
                )
                continue

            if cluster.sentiment_score >= self.strength_threshold:
                strengths.append(
                    CoreStrength(
                        feature=feature,
                        sentiment_score=cluster.sentiment_score,
                        mention_frequency=cluster.mention_frequency,
                        key_highlights=_positive_quotes(cluster),
                    )
                )
            elif cluster.sentiment_score < self.gap_threshold:
                neg_quotes = _negative_quotes(cluster)
                gaps.append(
                    FeatureGap(
                        feature=feature,
                        sentiment_score=cluster.sentiment_score,
                        gap_description=self.llm.summarize_gap(feature, neg_quotes),
                        mention_frequency=cluster.mention_frequency,
                    )
                )
            # else: mixed/neutral -> neither a headline strength nor a clear gap.

        strengths.sort(key=lambda s: (s.sentiment_score, s.mention_frequency), reverse=True)
        gaps.sort(key=lambda g: (g.sentiment_score, -g.mention_frequency))
        return FeatureAuditReport(core_strengths=strengths, feature_gaps=gaps)


def _positive_quotes(cluster: ClusterSentiment) -> List[str]:
    return list(cluster.representative_quotes[:2])


def _negative_quotes(cluster: ClusterSentiment) -> Sequence[str]:
    return cluster.representative_quotes
