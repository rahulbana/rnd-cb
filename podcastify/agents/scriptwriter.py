"""Script writer agent: turn an :class:`Article` into a 2-person dialogue."""

from __future__ import annotations

from typing import List

from ..models import Article, DialogueLine, PodcastScript, ScriptDraft, Speaker
from .base import LLMAgent


class ScriptWriterAgent(LLMAgent):
    name = "scriptwriter"
    system_prompt = (
        "You are an award-winning podcast script writer. You turn written "
        "articles into lively, natural two-person conversations between a "
        "host and a co-host. The conversation must:\n"
        "- Accurately convey ALL the key ideas and facts from the article.\n"
        "- Sound like real people talking: contractions, short turns, "
        "  reactions, the occasional 'right', 'yeah', 'that's a great point'.\n"
        "- Have the host guide the discussion and the co-host add analysis, "
        "  examples, and follow-up questions.\n"
        "- Open with a brief, friendly intro that names the show and topic, "
        "  and close with a short wrap-up and sign-off.\n"
        "- Avoid stage directions, sound effects, or text in brackets. Only "
        "  spoken words.\n"
        "- Use ONLY the two speaker names you are given."
    )

    def write(
        self,
        article: Article,
        speakers: List[Speaker],
        target_minutes: int = 5,
    ) -> PodcastScript:
        if len(speakers) != 2:
            raise ValueError("Exactly two speakers are required.")

        host, cohost = speakers
        # ~150 spoken words per minute is a good rule of thumb.
        target_words = target_minutes * 150

        prompt = f"""Write a two-person podcast conversation based on the article below.

SHOW HOSTS
- {host.name} ({host.role}): {host.persona or 'curious, warm, drives the conversation'}
- {cohost.name} ({cohost.role}): {cohost.persona or 'knowledgeable, adds depth and examples'}

REQUIREMENTS
- Roughly {target_words} words total (about {target_minutes} minutes spoken).
- Alternate speakers naturally; do not have one person monologue for long.
- Start with an intro, cover the article thoroughly, end with a sign-off.
- The "speaker" field of every line MUST be exactly "{host.name}" or "{cohost.name}".

ARTICLE TITLE: {article.title}
{f'AUTHOR: {article.author}' if article.author else ''}

ARTICLE BODY:
{article.text[:16000]}
"""

        draft = self.complete_structured(prompt, ScriptDraft)
        lines = self._normalize_lines(draft.lines, host, cohost)
        return PodcastScript(title=draft.title, speakers=speakers, lines=lines)

    def _normalize_lines(self, raw_lines, host: Speaker, cohost: Speaker):
        """Map any stray speaker labels back onto the two real speakers."""
        valid = {host.name.lower(): host.name, cohost.name.lower(): cohost.name}
        normalized: List[DialogueLine] = []
        last = cohost.name
        for ln in raw_lines:
            text = (ln.text or "").strip()
            if not text:
                continue
            name = valid.get((ln.speaker or "").strip().lower())
            if name is None:
                # Unknown label -> alternate from the previous speaker.
                name = host.name if last == cohost.name else cohost.name
            normalized.append(DialogueLine(speaker=name, text=text))
            last = name
        return normalized
