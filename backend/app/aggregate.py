"""Aggregate statistics over a batch of analysis results."""
from collections import Counter

from .schemas import AnalysisResult, BatchSummary, Sentiment


def summarize(results: list[AnalysisResult]) -> BatchSummary:
    """Compute aggregate stats used by the dashboard."""
    total = len(results)
    counts = Counter(r.overall for r in results)
    emotion_dist = Counter(r.emotion.value for r in results)

    pos_kw: Counter[str] = Counter()
    neg_kw: Counter[str] = Counter()
    for r in results:
        if r.overall in (Sentiment.positive, Sentiment.mixed):
            pos_kw.update(k.lower() for k in r.keywords)
        if r.overall in (Sentiment.negative, Sentiment.mixed):
            neg_kw.update(k.lower() for k in r.keywords)

    avg_score = round(sum(r.score for r in results) / total, 3) if total else 0.0
    avg_conf = round(sum(r.confidence for r in results) / total, 3) if total else 0.0

    return BatchSummary(
        total=total,
        positive=counts.get(Sentiment.positive, 0),
        negative=counts.get(Sentiment.negative, 0),
        neutral=counts.get(Sentiment.neutral, 0),
        mixed=counts.get(Sentiment.mixed, 0),
        average_score=avg_score,
        average_confidence=avg_conf,
        emotion_distribution=dict(emotion_dist),
        top_positive_keywords=[k for k, _ in pos_kw.most_common(10)],
        top_negative_keywords=[k for k, _ in neg_kw.most_common(10)],
    )
