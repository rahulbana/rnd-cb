"""Orchestrator that wires the agents together into one pipeline.

    URL / text
        -> ExtractorAgent      (clean -> Article)
        -> ScriptWriterAgent   (Article -> 2-person PodcastScript)
        -> EditorAgent         (polish for flow + TTS)
        -> VoiceAgent          (synthesize -> audio file)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .agents import EditorAgent, ExtractorAgent, ScriptWriterAgent, VoiceAgent
from .llm import LLMProvider, get_llm_provider
from .models import Article, PodcastScript, Speaker
from .tts import get_tts_backend

logger = logging.getLogger("podcastify")


@dataclass
class PipelineConfig:
    # --- LLM (swappable provider behind the LLMProvider interface) ---
    llm_provider: str = "openai"          # "openai" or any registered provider
    llm_model: str = "gpt-4o"             # provider-specific model id
    llm_api_key: Optional[str] = None     # falls back to the provider's env var

    # --- Podcast shape ---
    target_minutes: int = 5
    speakers: List[Speaker] = field(
        default_factory=lambda: [
            Speaker(
                name="Alex",
                role="host",
                persona="warm, curious host who keeps the conversation moving",
            ),
            Speaker(
                name="Sam",
                role="cohost",
                persona="sharp co-host who adds analysis, examples and questions",
            ),
        ]
    )

    # --- TTS (free / open source) ---
    tts_backend: str = "kokoro"  # "kokoro" or "piper"
    gap_seconds: float = 0.35

    # --- Behaviour ---
    run_editor: bool = True


@dataclass
class PodcastResult:
    article: Article
    script: PodcastScript
    audio_path: Optional[Path]
    transcript_path: Optional[Path]


class PodcastPipeline:
    """Runs the full article -> podcast conversion."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        """Build the pipeline.

        Pass ``provider`` to inject any :class:`LLMProvider` (e.g. a custom
        vendor or a test double); otherwise one is built from ``config``.
        """
        self.config = config or PipelineConfig()
        self.provider = provider or get_llm_provider(
            self.config.llm_provider,
            model=self.config.llm_model,
            api_key=self.config.llm_api_key,
        )

        self.extractor = ExtractorAgent(self.provider, temperature=0.2)
        self.scriptwriter = ScriptWriterAgent(self.provider, temperature=0.8)
        self.editor = EditorAgent(self.provider, temperature=0.4)

    # -- public API ---------------------------------------------------------

    def run(
        self,
        *,
        url: str | None = None,
        text: str | None = None,
        out_path: str | Path = "output/podcast.wav",
        write_transcript: bool = True,
        synth_audio: bool = True,
    ) -> PodcastResult:
        """Convert an article (URL or raw text) into a podcast.

        Set ``synth_audio=False`` to produce only the script/transcript
        (useful when TTS dependencies are not installed).
        """
        logger.info("Pipeline start")

        # 1. Extract & clean
        article = self.extractor.extract(url=url, text=text)
        logger.info("Article: %r (%d words)", article.title, article.word_count())

        # 2. Write the 2-person script
        script = self.scriptwriter.write(
            article, self.config.speakers, self.config.target_minutes
        )

        # 3. Edit / polish
        if self.config.run_editor:
            script = self.editor.polish(script)
        logger.info("Script ready: %d lines", len(script.lines))

        out_path = Path(out_path)

        # transcript
        transcript_path: Optional[Path] = None
        if write_transcript:
            transcript_path = out_path.with_suffix(".transcript.md")
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            transcript_path.write_text(script.transcript(), encoding="utf-8")
            logger.info("Transcript: %s", transcript_path)

        # 4. Synthesize audio
        audio_path: Optional[Path] = None
        if synth_audio:
            backend = get_tts_backend(self.config.tts_backend)
            voice_agent = VoiceAgent(backend, gap_seconds=self.config.gap_seconds)
            audio_path = voice_agent.render(script, out_path)

        logger.info("Pipeline done")
        return PodcastResult(
            article=article,
            script=script,
            audio_path=audio_path,
            transcript_path=transcript_path,
        )
