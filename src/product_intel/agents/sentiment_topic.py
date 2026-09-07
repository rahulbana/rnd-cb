"""Agent 2 - Review Sentiment & Topic Clustering.

Filters irrelevant feedback (courier/packaging), assigns each remaining review to
a functional dimension, and computes per-cluster sentiment distribution and an
overall sentiment ratio.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from .. import nlp
from ..config import DEFAULT_TOPIC, IRRELEVANT_KEYWORDS, TOPIC_KEYWORDS
from ..schemas import ClusterSentiment, IngestedProduct, Review, SentimentReport


class SentimentTopicAgent:
    def __init__(
        self,
        topic_keywords: Dict[str, Sequence[str]] = TOPIC_KEYWORDS,
        irrelevant_keywords: Sequence[str] = IRRELEVANT_KEYWORDS,
        default_topic: str = DEFAULT_TOPIC,
    ):
        self.topic_keywords = topic_keywords
        self.irrelevant_keywords = [k.lower() for k in irrelevant_keywords]
        self.default_topic = default_topic

    def _is_irrelevant(self, review: Review) -> bool:
        """Drop reviews that are purely about logistics, not the product itself.

        A review that also praises/criticizes the product is kept - only reviews
        dominated by delivery/packaging complaints are filtered.
        """

        text = f"{review.title} {review.body}".lower()
        if not any(kw in text for kw in self.irrelevant_keywords):
            return False
        # If the review still maps strongly to a product topic, keep it.
        topic = nlp.assign_topic(text, self.topic_keywords, self.default_topic)
        return topic == self.default_topic

    def run(self, ingested: IngestedProduct) -> SentimentReport:
        kept: List[Review] = []
        filtered = 0
        for r in ingested.reviews:
            if self._is_irrelevant(r):
                filtered += 1
            else:
                kept.append(r)

        buckets: Dict[str, List[Review]] = {}
        scores: Dict[str, List[float]] = {}
        for r in kept:
            text = f"{r.title} {r.body}"
            topic = nlp.assign_topic(text, self.topic_keywords, self.default_topic)
            buckets.setdefault(topic, []).append(r)
            scores.setdefault(topic, []).append(nlp.sentiment_score(text))

        clusters: List[ClusterSentiment] = []
        for topic, reviews in buckets.items():
            pos = neu = neg = 0
            quotes_pos: List[str] = []
            quotes_neg: List[str] = []
            for r, s in zip(reviews, scores[topic]):
                label = nlp.polarity_label(s)
                if label == "positive":
                    pos += 1
                    if len(quotes_pos) < 3:
                        quotes_pos.append(_snippet(r))
                elif label == "negative":
                    neg += 1
                    if len(quotes_neg) < 3:
                        quotes_neg.append(_snippet(r))
                else:
                    neu += 1
            avg = sum(scores[topic]) / len(scores[topic]) if scores[topic] else 0.0
            clusters.append(
                ClusterSentiment(
                    name=topic,
                    review_ids=[r.review_id for r in reviews],
                    mention_frequency=len(reviews),
                    positive=pos,
                    neutral=neu,
                    negative=neg,
                    sentiment_score=nlp.normalize_sentiment(avg),
                    representative_quotes=(quotes_pos + quotes_neg)[:4],
                )
            )
        clusters.sort(key=lambda c: c.mention_frequency, reverse=True)

        avg_star = (
            round(sum(r.rating for r in kept) / len(kept), 2) if kept else 0.0
        )
        positive_reviews = sum(
            1 for r in kept if nlp.polarity_label(nlp.sentiment_score(f"{r.title} {r.body}")) == "positive"
        )
        pos_ratio = round(positive_reviews / len(kept), 3) if kept else 0.0

        return SentimentReport(
            total_reviews_analyzed=len(kept),
            filtered_out=filtered,
            average_star_rating=avg_star,
            positive_sentiment_ratio=pos_ratio,
            clusters=clusters,
        )


def _snippet(review: Review, limit: int = 160) -> str:
    text = review.title.strip() or review.body.strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text
