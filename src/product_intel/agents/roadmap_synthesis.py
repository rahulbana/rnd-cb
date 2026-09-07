"""Agent 5 - Roadmap & Backlog Synthesis.

Ranks every defect and feature gap with a RICE score, assigns P0/P1/P2, and
emits concrete backlog tickets (user story, acceptance criteria, proposed action)
ready for a Jira/Linear export.
"""

from __future__ import annotations

from typing import List

from ..config import DEFAULT_WEIGHTS, ScoringWeights
from ..llm.base import LLMClient
from ..schemas import (
    BacklogItem,
    Defect,
    FeatureAuditReport,
    FeatureGap,
    Priority,
    RiceScore,
    SentimentReport,
)

# Effort heuristic by defect category / item kind (lower = cheaper).
_EFFORT_BY_CATEGORY = {
    "Functional Blocker": 2.0,
    "Usability Inconvenience": 1.5,
    "Aesthetic/Cosmetic": 1.0,
}
_FEATURE_EFFORT = 3.0


class RoadmapSynthesisAgent:
    def __init__(self, llm: LLMClient, weights: ScoringWeights = DEFAULT_WEIGHTS):
        self.llm = llm
        self.weights = weights

    # -- RICE ---------------------------------------------------------------- #
    def _rice_for_defect(self, defect: Defect) -> RiceScore:
        reach = round(defect.frequency_ratio * 100, 1)  # % of reviewers touched
        impact = round(defect.severity * 3, 2)  # 0-3 scale
        confidence = 0.9 if defect.frequency >= 5 else 0.7 if defect.frequency >= 2 else 0.5
        effort = _EFFORT_BY_CATEGORY.get(defect.category.value, 2.0)
        return RiceScore(reach=reach, impact=impact, confidence=confidence, effort=effort)

    def _rice_for_gap(self, gap: FeatureGap, total_reviews: int) -> RiceScore:
        reach = round((gap.mention_frequency / total_reviews * 100) if total_reviews else 0.0, 1)
        # lower sentiment => higher impact of fixing it
        impact = round((1.0 - gap.sentiment_score) * 2.5, 2)
        confidence = 0.8 if gap.mention_frequency >= 5 else 0.6 if gap.mention_frequency else 0.4
        return RiceScore(reach=reach, impact=impact, confidence=confidence, effort=_FEATURE_EFFORT)

    def _priority(self, rice: RiceScore) -> Priority:
        s = rice.score
        if s >= self.weights.p0_cutoff:
            return Priority.P0
        if s >= self.weights.p1_cutoff:
            return Priority.P1
        return Priority.P2

    # -- synthesis ---------------------------------------------------------- #
    def run(
        self,
        defects: List[Defect],
        audit: FeatureAuditReport,
        sentiment: SentimentReport,
    ) -> List[BacklogItem]:
        items: List[BacklogItem] = []

        for defect in defects:
            rice = self._rice_for_defect(defect)
            story, criteria = self.llm.draft_user_story(
                defect.title, "defect", defect.representative_quotes
            )
            items.append(
                BacklogItem(
                    ticket_id="",  # assigned after global ranking
                    type="Defect / Bug",
                    priority=self._priority(rice),
                    title=defect.title,
                    frequency_impact=f"{round(defect.frequency_ratio * 100, 1)}% of all reviews",
                    proposed_action=self.llm.propose_action(
                        defect.title, defect.category.value, defect.representative_quotes
                    ),
                    rice=rice,
                    user_story=story,
                    acceptance_criteria=criteria,
                )
            )

        for gap in audit.feature_gaps:
            rice = self._rice_for_gap(gap, sentiment.total_reviews_analyzed)
            story, criteria = self.llm.draft_user_story(
                f"Improve {gap.feature}", "feature", [gap.gap_description]
            )
            items.append(
                BacklogItem(
                    ticket_id="",
                    type="Feature Enhancement",
                    priority=self._priority(rice),
                    title=f"Improve {gap.feature}",
                    frequency_impact=(
                        f"{round(gap.mention_frequency / sentiment.total_reviews_analyzed * 100, 1)}% of reviews"
                        if sentiment.total_reviews_analyzed and gap.mention_frequency
                        else "advertised feature unvalidated by reviews"
                    ),
                    proposed_action=self.llm.propose_action(
                        f"Improve {gap.feature}", "Feature Enhancement", [gap.gap_description]
                    ),
                    rice=rice,
                    user_story=story,
                    acceptance_criteria=criteria,
                )
            )

        # Global ranking: priority first, then RICE score.
        _priority_rank = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2}
        items.sort(key=lambda it: (_priority_rank[it.priority], -(it.rice.score if it.rice else 0)))
        for i, it in enumerate(items):
            it.ticket_id = f"VNXT-{101 + i}"
        return items
