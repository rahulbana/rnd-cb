"""Editor agent: polish the draft script for flow and TTS-friendliness."""

from __future__ import annotations

from ..models import PodcastScript, ScriptDraft, DialogueLine
from .base import LLMAgent


class EditorAgent(LLMAgent):
    name = "editor"
    system_prompt = (
        "You are a podcast script editor. You receive a two-person dialogue "
        "and improve it WITHOUT changing who says what fundamentally. Your job:\n"
        "- Smooth awkward phrasing and remove repetition.\n"
        "- Make hand-offs between the two speakers feel natural.\n"
        "- Expand symbols/abbreviations into spoken form (e.g. '%' -> 'percent', "
        "  '$5' -> 'five dollars', 'e.g.' -> 'for example') so a text-to-speech "
        "  engine reads them correctly.\n"
        "- Remove any bracketed stage directions or sound-effect notes.\n"
        "- Keep both speakers' names exactly as given.\n"
        "Return the full edited conversation."
    )

    def polish(self, script: PodcastScript) -> PodcastScript:
        names = [s.name for s in script.speakers]
        body = "\n".join(f"{ln.speaker}: {ln.text}" for ln in script.lines)
        prompt = (
            f"The two speakers are: {names[0]} and {names[1]}.\n"
            "Edit and return the conversation below. Keep it the same length "
            "or slightly tighter. Use only these two speaker names.\n\n"
            f"TITLE: {script.title}\n\n{body}"
        )
        draft = self.complete_structured(prompt, ScriptDraft)

        valid = {n.lower(): n for n in names}
        lines = []
        last = names[1]
        for ln in draft.lines:
            text = (ln.text or "").strip()
            if not text:
                continue
            name = valid.get((ln.speaker or "").strip().lower())
            if name is None:
                name = names[0] if last == names[1] else names[1]
            lines.append(DialogueLine(speaker=name, text=text))
            last = name

        if not lines:  # fall back to the unedited script if editing failed
            return script
        return PodcastScript(
            title=draft.title or script.title,
            speakers=script.speakers,
            lines=lines,
        )
