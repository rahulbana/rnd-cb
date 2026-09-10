"""Sentiment/emotion analysis engine.

Uses the OpenAI API with structured JSON output when an API key is configured.
Falls back to a lightweight lexicon-based analyzer so the app is fully usable
for development/demo without a key.
"""
from __future__ import annotations

import json
import re

from .config import get_settings
from .schemas import AnalysisResult, Emotion, Sentiment

EMOTIONS = [e.value for e in Emotion]

SYSTEM_PROMPT = """You are an expert sentiment and emotion analysis engine.
Analyze the user's text and return a single JSON object. Be precise and concise.

Rules:
- "overall" must be one of: positive, negative, neutral, mixed. Use "mixed" when
  the text contains clearly both positive and negative sentiment.
- "score" is a float from -1.0 (very negative) to 1.0 (very positive).
- "confidence" is a float from 0.0 to 1.0.
- "emotion" is the single dominant emotion, one of: joy, trust, anticipation,
  surprise, sadness, anger, fear, disgust, neutral.
- "emotion_scores" maps each of those emotions to an intensity 0.0-1.0.
- "positive_aspects" / "negative_aspects" are short topic labels
  (e.g. "Product quality", "Delivery speed"), not full sentences.
- "keywords" are the most salient words or short phrases from the text.
- "summary" is a single short sentence describing the sentiment."""

JSON_SCHEMA = {
    "name": "sentiment_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "overall": {
                "type": "string",
                "enum": ["positive", "negative", "neutral", "mixed"],
            },
            "score": {"type": "number"},
            "confidence": {"type": "number"},
            "emotion": {"type": "string", "enum": EMOTIONS},
            "emotion_scores": {
                "type": "object",
                "additionalProperties": False,
                "properties": {e: {"type": "number"} for e in EMOTIONS},
                "required": EMOTIONS,
            },
            "positive_aspects": {"type": "array", "items": {"type": "string"}},
            "negative_aspects": {"type": "array", "items": {"type": "string"}},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
        },
        "required": [
            "overall",
            "score",
            "confidence",
            "emotion",
            "emotion_scores",
            "positive_aspects",
            "negative_aspects",
            "keywords",
            "summary",
        ],
    },
}


# ---------------------------------------------------------------------------
# OpenAI-backed analyzer
# ---------------------------------------------------------------------------
_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(api_key=get_settings().openai_api_key)
    return _client


def _analyze_with_openai(text: str) -> AnalysisResult:
    settings = get_settings()
    client = _get_client()
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        temperature=0,
    )
    data = json.loads(completion.choices[0].message.content)
    data["text"] = text
    return AnalysisResult(**data)


# ---------------------------------------------------------------------------
# Fallback lexicon-based analyzer (used when no API key is configured)
# ---------------------------------------------------------------------------
POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "awesome", "love", "loved", "like",
    "wonderful", "fantastic", "happy", "pleased", "perfect", "best", "nice",
    "helpful", "fast", "friendly", "recommend", "satisfied", "beautiful",
    "reliable", "smooth", "quality", "impressed", "brilliant", "delightful",
}
NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "hate", "hated", "poor", "worst", "slow",
    "broken", "disappointed", "disappointing", "horrible", "annoying", "buggy",
    "expensive", "rude", "useless", "unreliable", "delay", "delayed", "problem",
    "issue", "fail", "failed", "waste", "difficult", "confusing", "cheap",
}
EMOTION_WORDS = {
    "joy": {"happy", "love", "delight", "great", "excellent", "enjoy", "glad"},
    "trust": {"reliable", "trust", "recommend", "quality", "dependable", "safe"},
    "anticipation": {"soon", "waiting", "expect", "hope", "upcoming", "await"},
    "surprise": {"surprised", "unexpected", "wow", "shocking", "amazing"},
    "sadness": {"sad", "disappointed", "unhappy", "sorry", "miss", "regret"},
    "anger": {"angry", "furious", "hate", "rude", "annoying", "frustrated"},
    "fear": {"afraid", "worried", "scared", "anxious", "concern", "risk"},
    "disgust": {"disgusting", "gross", "awful", "horrible", "nasty"},
}
STOPWORDS = {
    "the", "a", "an", "is", "was", "are", "were", "be", "been", "to", "of",
    "and", "or", "but", "in", "on", "at", "for", "with", "it", "this", "that",
    "i", "you", "we", "they", "he", "she", "my", "our", "your", "very", "so",
    "not", "no", "as", "if", "then", "than", "too", "also", "just", "really",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _analyze_with_lexicon(text: str) -> AnalysisResult:
    tokens = _tokenize(text)
    pos_hits = [t for t in tokens if t in POSITIVE_WORDS]
    neg_hits = [t for t in tokens if t in NEGATIVE_WORDS]

    pos, neg = len(pos_hits), len(neg_hits)
    total = pos + neg
    score = round((pos - neg) / total, 2) if total else 0.0

    if pos and neg:
        overall = Sentiment.mixed
    elif score > 0.15:
        overall = Sentiment.positive
    elif score < -0.15:
        overall = Sentiment.negative
    else:
        overall = Sentiment.neutral

    confidence = round(min(0.95, 0.4 + 0.1 * total), 2)

    emotion_scores = {e: 0.0 for e in EMOTIONS}
    for emotion, words in EMOTION_WORDS.items():
        matches = sum(1 for t in tokens if t in words)
        if matches:
            emotion_scores[emotion] = round(min(1.0, 0.3 + 0.2 * matches), 2)
    if not any(emotion_scores.values()):
        emotion_scores["neutral"] = 0.5
    emotion = max(emotion_scores, key=emotion_scores.get)

    keywords = []
    for t in tokens:
        if t not in STOPWORDS and len(t) > 2 and t not in keywords:
            keywords.append(t)
    keywords = keywords[:8]

    return AnalysisResult(
        text=text,
        overall=overall,
        score=score,
        confidence=confidence,
        emotion=Emotion(emotion),
        emotion_scores=emotion_scores,
        positive_aspects=list(dict.fromkeys(pos_hits))[:5],
        negative_aspects=list(dict.fromkeys(neg_hits))[:5],
        keywords=keywords,
        summary=f"Detected {overall.value} sentiment (lexicon fallback).",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyze_text(text: str) -> AnalysisResult:
    """Analyze a single piece of text, using OpenAI when available."""
    text = text.strip()
    if not text:
        raise ValueError("Text must not be empty.")
    if get_settings().has_openai:
        return _analyze_with_openai(text)
    return _analyze_with_lexicon(text)


def using_openai() -> bool:
    """Whether analysis is backed by OpenAI (vs. the lexicon fallback)."""
    return get_settings().has_openai
