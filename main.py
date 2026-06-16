#!/usr/bin/env python3
"""Command-line entrypoint for Podcastify.

Examples
--------
    # From a URL, default Kokoro voices, ~6 minute episode
    python main.py --url https://example.com/blog-post --minutes 6

    # From a local text file, custom host names
    python main.py --file examples/sample_article.txt \
        --host Maya --cohost Leo --out output/episode.wav

    # Script/transcript only (no TTS deps needed)
    python main.py --file examples/sample_article.txt --no-audio
"""

from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv

from podcastify import PodcastPipeline, PipelineConfig, Speaker


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert an article/blog into a 2-person audio podcast."
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="URL of the article/blog to convert.")
    src.add_argument("--file", help="Path to a local .txt article file.")
    src.add_argument("--text", help="Raw article text passed directly.")

    p.add_argument("--out", default="output/podcast.wav",
                   help="Output audio path (.wav or .mp3). Default: output/podcast.wav")
    p.add_argument("--minutes", type=int, default=5,
                   help="Approximate target length in minutes. Default: 5")

    p.add_argument("--host", default="Alex", help="Host name. Default: Alex")
    p.add_argument("--cohost", default="Sam", help="Co-host name. Default: Sam")
    p.add_argument("--host-voice", default="", help="TTS voice id for the host.")
    p.add_argument("--cohost-voice", default="", help="TTS voice id for the co-host.")

    p.add_argument("--provider", default="openai",
                   help="LLM provider for the agents. Default: openai")
    p.add_argument("--model", default="gpt-4o",
                   help="LLM model id for the agents. Default: gpt-4o")
    p.add_argument("--tts", default="kokoro", choices=["kokoro", "piper"],
                   help="Open-source TTS backend. Default: kokoro")

    p.add_argument("--no-editor", action="store_true",
                   help="Skip the editor polishing pass.")
    p.add_argument("--no-audio", action="store_true",
                   help="Produce only the script/transcript (no TTS).")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
    )

    text = None
    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read()

    config = PipelineConfig(
        llm_provider=args.provider,
        llm_model=args.model,
        target_minutes=args.minutes,
        tts_backend=args.tts,
        run_editor=not args.no_editor,
        speakers=[
            Speaker(name=args.host, role="host",
                    persona="warm, curious host who keeps the conversation moving",
                    voice=args.host_voice),
            Speaker(name=args.cohost, role="cohost",
                    persona="sharp co-host who adds analysis, examples and questions",
                    voice=args.cohost_voice),
        ],
    )

    try:
        pipeline = PodcastPipeline(config)
        result = pipeline.run(
            url=args.url,
            text=text,
            out_path=args.out,
            synth_audio=not args.no_audio,
        )
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1

    print("\n=== Done ===")
    print(f"Title:      {result.script.title}")
    print(f"Speakers:   {', '.join(s.name for s in result.script.speakers)}")
    print(f"Lines:      {len(result.script.lines)}")
    if result.transcript_path:
        print(f"Transcript: {result.transcript_path}")
    if result.audio_path:
        print(f"Audio:      {result.audio_path}")
    else:
        print("Audio:      (skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
