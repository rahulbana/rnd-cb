"""Shared data models passed between agents in the pipeline."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class Article(BaseModel):
    """Cleaned source content extracted from a URL or raw text."""

    title: str = Field(default="Untitled", description="Article title.")
    author: str | None = Field(default=None, description="Author, if known.")
    source_url: str | None = Field(default=None, description="Original URL, if any.")
    text: str = Field(description="Cleaned main body text of the article.")

    def word_count(self) -> int:
        return len(self.text.split())


class Speaker(BaseModel):
    """One of the two podcast hosts."""

    name: str
    role: Literal["host", "cohost"] = "host"
    # Persona / speaking style used to steer the script writer.
    persona: str = ""
    # Voice id understood by the chosen TTS backend.
    voice: str = ""


class DialogueLine(BaseModel):
    """A single spoken turn in the conversation."""

    speaker: str = Field(description="Name of the speaker (must match a Speaker).")
    text: str = Field(description="What the speaker says, in natural spoken English.")


class PodcastScript(BaseModel):
    """The full two-person conversation produced by the script writer."""

    title: str = Field(description="Catchy episode title.")
    speakers: List[Speaker] = Field(description="The two podcast hosts.")
    lines: List[DialogueLine] = Field(description="Ordered conversation turns.")

    def transcript(self) -> str:
        """Render a human-readable transcript."""
        out = [f"# {self.title}", ""]
        for line in self.lines:
            out.append(f"**{line.speaker}:** {line.text}")
            out.append("")
        return "\n".join(out)


# --- Structured-output schemas used for OpenAI responses -------------------
# These mirror what we ask the LLM to return so we can parse it reliably.


class _ScriptLine(BaseModel):
    speaker: str
    text: str


class ScriptDraft(BaseModel):
    """Schema the LLM fills in when drafting / editing the conversation."""

    title: str
    lines: List[_ScriptLine]
