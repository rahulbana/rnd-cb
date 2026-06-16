"""Turn raw articles into an exam-ready brief using an OpenAI LLM.

Strategy: **map-reduce** to stay cheap and within context limits.
  * MAP   — each batch of articles is distilled into UPSC-relevant bullets,
            grouped by subject, with everything exam-irrelevant discarded.
  * REDUCE— the per-batch results are merged, de-duplicated and re-ordered
            into a single clean brief.

Only OpenAI is used (per requirement). The client is created lazily so the
rest of the package can be imported without the SDK installed.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from .config import Config
from .models import Article, Brief

logger = logging.getLogger(__name__)

# Canonical subjects mirroring the UPSC GS syllabus. Keeping a fixed taxonomy
# lets the reduce step merge batches reliably and keeps the document tidy.
SUBJECTS: tuple[str, ...] = (
    "Polity & Governance",
    "Economy",
    "International Relations",
    "Environment & Ecology",
    "Science & Technology",
    "Government Schemes & Policies",
    "Reports, Indices & Appointments",
    "History, Art & Culture",
    "Miscellaneous (Prelims Facts)",
)

_MAP_SYSTEM = (
    "You are a senior UPSC (Indian Civil Services) current-affairs faculty "
    "member. You read raw news items and extract ONLY what a serious aspirant "
    "must know for General Studies. Ruthlessly discard sports scores, celebrity/"
    "entertainment gossip, crime blotter, local civic trivia, stock tips, "
    "opinion fluff and advertisements. Keep policy, governance, economy, IR, "
    "environment, science & tech, schemes, reports/indices, appointments and "
    "static-linked facts. Each point must be self-contained, factual, neutral "
    "and one or two crisp sentences — no filler."
)

_REDUCE_SYSTEM = (
    "You are an editor compiling a UPSC daily current-affairs brief. You merge "
    "several partial notes into one clean set, removing duplicates and near-"
    "duplicates, keeping the single best-worded version of each point, and "
    "ordering points within each subject from most to least exam-relevant."
)


def _subjects_clause() -> str:
    return ", ".join(f'"{s}"' for s in SUBJECTS)


class OpenAISummarizer:
    """Wraps the OpenAI chat API for the map and reduce passes."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._client = None  # lazily initialised

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI  # imported lazily

            self._client = OpenAI(api_key=self.config.openai_api_key)
        return self._client

    def _chat_json(self, system: str, user: str) -> dict:
        """Single chat completion that must return a JSON object."""
        resp = self.client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON content; skipping batch")
            return {}

    def _map_batch(self, batch: list[Article]) -> dict[str, list[str]]:
        blocks = "\n".join(a.as_prompt_block() for a in batch)
        user = (
            "From the news items below, produce UPSC-relevant points grouped by "
            f"subject. Allowed subjects (use these exact keys): {_subjects_clause()}.\n"
            "Return a JSON object shaped as {\"sections\": {\"<subject>\": "
            "[\"point\", ...]}}. Omit subjects with no relevant point. If an item "
            "has no exam value, drop it entirely.\n\n"
            f"NEWS ITEMS:\n{blocks}"
        )
        data = self._chat_json(_MAP_SYSTEM, user)
        return _coerce_sections(data.get("sections", {}))

    def _reduce(self, partials: list[dict[str, list[str]]]) -> dict[str, list[str]]:
        merged = _merge_sections(partials)
        if not merged:
            return {}
        # If the merged set is small there is nothing to gain from another call.
        total_points = sum(len(v) for v in merged.values())
        if total_points <= 8:
            return merged

        user = (
            "Merge and clean the following partial UPSC notes. Remove duplicates "
            "and near-duplicates, keep the best wording, and order each subject's "
            "points by exam relevance. Keep the same subject keys. Return JSON as "
            '{"sections": {"<subject>": ["point", ...]}}.\n\n'
            f"PARTIAL NOTES:\n{json.dumps({'sections': merged}, ensure_ascii=False)}"
        )
        data = self._chat_json(_REDUCE_SYSTEM, user)
        cleaned = _coerce_sections(data.get("sections", {}))
        return cleaned or merged  # fall back to the deterministic merge

    def summarize(self, articles: list[Article]) -> Brief:
        """Run the full map-reduce and return a :class:`Brief`."""
        batches = _chunk(articles, self.config.batch_size)
        logger.info(
            "Summarising %d articles in %d batch(es)", len(articles), len(batches)
        )
        partials = [self._map_batch(b) for b in batches]
        sections = self._reduce(partials)

        # Order sections per the canonical syllabus order for a stable document.
        ordered = {s: sections[s] for s in SUBJECTS if sections.get(s)}
        # Preserve any unexpected keys the model may have invented.
        for key, points in sections.items():
            if key not in ordered and points:
                ordered[key] = points

        return Brief(
            generated_at=datetime.now(timezone.utc),
            article_count=len(articles),
            source_count=len({a.source for a in articles}),
            sections=ordered,
        )


# --- pure helpers (no I/O, easily testable) ---------------------------------

def _chunk(items: list, size: int) -> list[list]:
    size = max(1, size)
    return [items[i : i + size] for i in range(0, len(items), size)]


def _coerce_sections(raw) -> dict[str, list[str]]:
    """Defensively normalise whatever the model returned into {str: [str]}."""
    out: dict[str, list[str]] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        points = value if isinstance(value, list) else [value]
        clean = [str(p).strip() for p in points if str(p).strip()]
        if clean:
            out[key.strip()] = clean
    return out


def _merge_sections(partials: list[dict[str, list[str]]]) -> dict[str, list[str]]:
    """Deterministically merge partials, dropping exact-duplicate points."""
    merged: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    for part in partials:
        for subject, points in part.items():
            bucket = merged.setdefault(subject, [])
            seen_set = seen.setdefault(subject, set())
            for point in points:
                fingerprint = "".join(ch for ch in point.lower() if ch.isalnum())[:120]
                if fingerprint in seen_set:
                    continue
                seen_set.add(fingerprint)
                bucket.append(point)
    return merged
