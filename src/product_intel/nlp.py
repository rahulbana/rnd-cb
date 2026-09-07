"""Dependency-free NLP helpers used by the analysis agents.

The architecture plan calls for dense embeddings, HDBSCAN/pgvector clustering
and topic classifiers. To keep the reference pipeline runnable offline and in
CI, this module provides deterministic, standard-library implementations of the
same building blocks:

* a bag-of-words vectorizer + cosine similarity (stands in for dense embeddings),
* threshold agglomerative clustering (stands in for HDBSCAN),
* a lexicon sentiment scorer, and
* keyword-based topic assignment.

Everything here is pure and deterministic, which makes the agents easy to test.
Swapping in real embeddings/clustering later only means replacing these
functions, not the agents that call them.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Sequence, Tuple

_TOKEN_RE = re.compile(r"[a-z0-9']+")

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "at", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she", "we",
    "they", "them", "my", "your", "our", "their", "so", "very", "just", "too",
    "as", "not", "no", "do", "does", "did", "have", "has", "had", "would", "will",
    "can", "could", "should", "up", "out", "about", "than", "then", "when", "while",
    "there", "here", "into", "over", "after", "before", "also", "get", "got",
}


def tokenize(text: str) -> List[str]:
    """Lowercase word tokens with stopwords removed."""

    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def bag_of_words(text: str) -> Counter:
    return Counter(tokenize(text))


def cosine(a: Counter, b: Counter) -> float:
    """Cosine similarity between two sparse term-frequency vectors."""

    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    if dot == 0:
        return 0.0
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb)


# --------------------------------------------------------------------------- #
# Sentiment
# --------------------------------------------------------------------------- #
_POSITIVE = {
    "good", "great", "excellent", "amazing", "awesome", "love", "loved", "loves",
    "perfect", "fantastic", "superb", "comfortable", "clear", "crisp", "solid",
    "reliable", "impressive", "recommend", "recommended", "worth", "best", "nice",
    "happy", "satisfied", "quality", "premium", "smooth", "effective", "wonderful",
    "sturdy", "durable", "responsive", "intuitive", "seamless", "outstanding",
}
_NEGATIVE = {
    "bad", "terrible", "awful", "poor", "hate", "hated", "broke", "broken",
    "defective", "faulty", "disappointing", "disappointed", "useless", "cheap",
    "flimsy", "uncomfortable", "painful", "annoying", "frustrating", "frustrated",
    "buggy", "crash", "crashes", "crashing", "fails", "failed", "failure", "stutter",
    "stuttering", "drops", "dropping", "dropped", "glitch", "glitchy", "laggy",
    "lag", "unreliable", "worst", "waste", "return", "returned", "refund",
    "overheat", "overheating", "hot", "drains", "draining", "dead", "unusable",
    "disconnect", "disconnects", "disconnecting", "issue", "issues", "problem",
    "problems", "wobbly", "leak", "leaks", "scratches", "scratched",
}
_NEGATORS = {"not", "no", "never", "don't", "doesn't", "didn't", "isn't", "wasn't", "can't", "won't"}


def sentiment_score(text: str) -> float:
    """Lexicon sentiment in the range -1.0 (negative) .. 1.0 (positive).

    A simple one-token negation window flips polarity, so "not comfortable"
    counts as negative.
    """

    tokens = _TOKEN_RE.findall(text.lower())
    score = 0
    hits = 0
    for i, tok in enumerate(tokens):
        polarity = 0
        if tok in _POSITIVE:
            polarity = 1
        elif tok in _NEGATIVE:
            polarity = -1
        if polarity == 0:
            continue
        prev = tokens[i - 1] if i > 0 else ""
        if prev in _NEGATORS:
            polarity = -polarity
        score += polarity
        hits += 1
    if hits == 0:
        return 0.0
    return max(-1.0, min(1.0, score / hits))


def polarity_label(score: float, *, neutral_band: float = 0.15) -> str:
    if score > neutral_band:
        return "positive"
    if score < -neutral_band:
        return "negative"
    return "neutral"


def normalize_sentiment(score: float) -> float:
    """Map a -1..1 sentiment onto a 0..1 score."""

    return round((score + 1.0) / 2.0, 3)


# --------------------------------------------------------------------------- #
# Topic assignment
# --------------------------------------------------------------------------- #
def assign_topic(text: str, topic_keywords: Dict[str, Sequence[str]], default: str) -> str:
    """Assign ``text`` to the topic whose keywords it best matches.

    Deterministic: highest keyword-hit count wins, ties broken by topic order.
    """

    tokens = set(tokenize(text))
    raw = text.lower()
    best_topic = default
    best_hits = 0
    for topic, keywords in topic_keywords.items():
        hits = 0
        for kw in keywords:
            if " " in kw:
                if kw in raw:
                    hits += 1
            elif kw in tokens:
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best_topic = topic
    return best_topic


# --------------------------------------------------------------------------- #
# Clustering
# --------------------------------------------------------------------------- #
def agglomerative_cluster(
    vectors: Sequence[Counter], threshold: float = 0.18
) -> List[List[int]]:
    """Single-link agglomerative clustering by cosine threshold.

    Returns a list of clusters, each a list of item indices. Deterministic and
    order-stable. Used as an offline stand-in for HDBSCAN when reviews are not
    pre-labelled with a topic.
    """

    clusters: List[List[int]] = []
    centroids: List[Counter] = []
    for idx, vec in enumerate(vectors):
        best_c = -1
        best_sim = threshold
        for ci, centroid in enumerate(centroids):
            sim = cosine(vec, centroid)
            if sim >= best_sim:
                best_sim = sim
                best_c = ci
        if best_c == -1:
            clusters.append([idx])
            centroids.append(Counter(vec))
        else:
            clusters[best_c].append(idx)
            centroids[best_c].update(vec)
    return clusters


def top_terms(vectors: Iterable[Counter], n: int = 5) -> List[Tuple[str, int]]:
    total: Counter = Counter()
    for v in vectors:
        total.update(v)
    return total.most_common(n)
