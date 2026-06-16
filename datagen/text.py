"""Template-based text generation.

This module produces synthetic natural-language data with **zero** external
model dependencies, which keeps the agent self-contained and reproducible.
Two things live here:

1. :func:`random_sentences` – filler text for ``text`` feature columns.
2. Dataset builders for the ``text_classification`` and ``summarization``
   tasks, where the generated text is correlated with a label / summary so the
   data is actually learnable rather than pure noise.

The vocabulary is organised by topic so a text-classification dataset has a
real, recoverable signal: documents of class *finance* draw from finance
words, *sports* from sports words, and so on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_FILLER = (
    "the a an and or of to in on for with from by about into over after "
    "system data value record sample model result process signal note item "
    "report case study point level group set field metric trend output"
).split()

# Topic vocabularies used to make text-classification signal recoverable.
TOPICS: dict[str, list[str]] = {
    "finance": (
        "market stock investment portfolio dividend revenue profit earnings "
        "interest rate bond equity trading capital fiscal budget inflation "
        "currency loan asset liability balance"
    ).split(),
    "sports": (
        "team player score match tournament league goal coach season stadium "
        "championship victory defeat athlete training referee penalty striker "
        "defender midfield final"
    ).split(),
    "technology": (
        "software hardware algorithm network server database cloud processor "
        "application interface protocol encryption latency bandwidth firmware "
        "compiler runtime kernel module deployment"
    ).split(),
    "health": (
        "patient doctor treatment diagnosis symptom therapy clinic medicine "
        "vaccine recovery wellness nutrition immune disease surgery hospital "
        "prescription dosage diet exercise"
    ).split(),
    "politics": (
        "election government policy senate vote campaign parliament minister "
        "legislation diplomacy democracy candidate referendum coalition reform "
        "treaty governance ballot mandate cabinet"
    ).split(),
}

_SENTIMENT = {
    "positive": (
        "excellent great love wonderful amazing fantastic delighted pleased "
        "superb brilliant outstanding enjoyable recommend perfect happy best"
    ).split(),
    "negative": (
        "terrible awful hate disappointing horrible poor frustrated broken "
        "useless worst annoying refund slow defective unhappy avoid"
    ).split(),
    "neutral": (
        "okay average fine standard ordinary typical moderate acceptable "
        "reasonable adequate usual plain regular fair normal"
    ).split(),
}

_TEMPLATES = [
    "The {a} report highlights {b} and {c} across the {d}.",
    "Analysts noted that {a} influenced {b} during the {c} period.",
    "A new {a} approach to {b} improved {c} significantly.",
    "Observers discussed {a}, {b}, and the role of {c}.",
    "This {a} update covers {b}, {c}, and ongoing {d}.",
]


def random_sentences(
    rng: np.random.Generator, n: int, words: tuple[int, int] = (8, 24)
) -> np.ndarray:
    """Generate ``n`` filler sentences of random length within ``words``."""
    lo, hi = words
    lo = max(1, lo)
    hi = max(lo, hi)
    out = []
    for _ in range(n):
        length = int(rng.integers(lo, hi + 1))
        chosen = rng.choice(_FILLER, size=length)
        sentence = " ".join(chosen)
        out.append(sentence[0].upper() + sentence[1:] + ".")
    return np.array(out, dtype=object)


def _topic_document(
    rng: np.random.Generator, vocab: list[str], words: tuple[int, int]
) -> str:
    lo, hi = words
    length = int(rng.integers(max(4, lo), max(max(4, lo) + 1, hi + 1)))
    # 70% topic words, 30% filler — strong but not perfect signal.
    parts = []
    for _ in range(length):
        pool = vocab if rng.random() < 0.7 else _FILLER
        parts.append(str(rng.choice(pool)))
    sentence = " ".join(parts)
    return sentence[0].upper() + sentence[1:] + "."


def generate_text_classification(
    rng: np.random.Generator,
    n_rows: int,
    labels: list[str] | None = None,
    flavor: str = "topic",
    words: tuple[int, int] = (12, 40),
    target_name: str = "label",
) -> pd.DataFrame:
    """Build a ``(text, label)`` dataset with a recoverable signal.

    Args:
        flavor: ``"topic"`` uses topical vocabularies; ``"sentiment"`` uses
            positive/negative/neutral vocabularies.
        labels: Subset of available labels to use; defaults to all.
    """
    vocab_map = _SENTIMENT if flavor == "sentiment" else TOPICS
    available = list(vocab_map)
    if labels:
        unknown = set(labels) - set(available)
        if unknown:
            raise ValueError(
                f"Unknown {flavor} labels {sorted(unknown)}; available: {available}."
            )
        available = labels

    chosen_labels = rng.choice(available, size=n_rows)
    texts = [
        _topic_document(rng, vocab_map[label], words) for label in chosen_labels
    ]
    return pd.DataFrame({"text": texts, target_name: chosen_labels})


def generate_summarization(
    rng: np.random.Generator,
    n_rows: int,
    sentences_per_doc: tuple[int, int] = (4, 8),
    words: tuple[int, int] = (10, 20),
) -> pd.DataFrame:
    """Build ``(document, summary)`` pairs.

    The summary is an extractive first-sentence-style condensation of the
    document, so models trained on it have a consistent target to learn.
    """
    topics = list(TOPICS)
    docs, summaries = [], []
    lo_s, hi_s = sentences_per_doc
    for _ in range(n_rows):
        topic = str(rng.choice(topics))
        vocab = TOPICS[topic]
        n_sent = int(rng.integers(lo_s, hi_s + 1))
        sentences = [_topic_document(rng, vocab, words) for _ in range(n_sent)]
        document = " ".join(sentences)
        # Summary: the lead sentence plus the topic keyword framing.
        summary = f"This {topic} piece discusses {str(rng.choice(vocab))} and {str(rng.choice(vocab))}."
        docs.append(document)
        summaries.append(summary)
    return pd.DataFrame({"document": docs, "summary": summaries})
