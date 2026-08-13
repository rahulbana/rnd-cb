"""Command-line interface for the test-generation agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .collector import collect
from .env import load_dotenv
from .generator import generate_for_file
from .llm import LLMError, build_provider


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testgen",
        description="LLM-powered agent that writes test cases for a file or a "
        "whole project. Backends: OpenAI (default) or Ollama.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  testgen path/to/module.py\n"
            "  testgen ./src --provider ollama --model llama3\n"
            "  testgen app.py -d 'focus on the auth edge cases' --overwrite\n"
            "  testgen ./src -o ./tests --exclude '*/migrations/*' --dry-run\n"
        ),
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a source file or a project directory.",
    )
    parser.add_argument(
        "-d", "--description",
        help="Optional natural-language guidance for the tests.",
    )

    prov = parser.add_argument_group("model / provider")
    prov.add_argument(
        "--provider", default="openai", choices=["openai", "ollama"],
        help="LLM backend (default: openai).",
    )
    prov.add_argument("--model", help="Model name (default: gpt-4o-mini / llama3).")
    prov.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    prov.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout (seconds).")
    prov.add_argument("--api-key", help="OpenAI API key (else uses OPENAI_API_KEY).")
    prov.add_argument("--base-url", help="OpenAI-compatible base URL.")
    prov.add_argument("--ollama-host", help="Ollama host (default: http://localhost:11434).")
    prov.add_argument(
        "--env-file",
        help="Path to a .env file with keys like OPENAI_API_KEY "
        "(default: nearest .env found from the current directory upward).",
    )

    out = parser.add_argument_group("output / selection")
    out.add_argument(
        "-o", "--output-dir", type=Path,
        help="Write tests under this directory (mirrors the source tree). "
        "Default: alongside each source file.",
    )
    out.add_argument("--include", action="append", help="Glob to include (repeatable).")
    out.add_argument("--exclude", action="append", help="Glob to exclude (repeatable).")
    out.add_argument("--overwrite", action="store_true", help="Overwrite existing test files.")
    out.add_argument("--dry-run", action="store_true", help="Generate but don't write files.")

    parser.add_argument("--version", action="version", version=f"testgen {__version__}")
    return parser


def _root_for(path: Path) -> Path:
    path = path.expanduser().resolve()
    return path if path.is_dir() else path.parent


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Populate os.environ from a .env file (shell env still takes precedence).
    # If --env-file is given explicitly, fail loudly when it's missing.
    if args.env_file:
        if not load_dotenv(args.env_file):
            print(f"error: env file not found: {args.env_file}", file=sys.stderr)
            return 2
    else:
        load_dotenv()

    target = args.path.expanduser().resolve()
    if not target.exists():
        print(f"error: path not found: {target}", file=sys.stderr)
        return 2

    files = collect(target, include=args.include, exclude=args.exclude)
    if not files:
        print("No supported source files found to test.", file=sys.stderr)
        return 1

    try:
        provider = build_provider(
            args.provider,
            model=args.model,
            temperature=args.temperature,
            timeout=args.timeout,
            api_key=args.api_key,
            base_url=args.base_url,
            host=args.ollama_host,
        )
    except LLMError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    root = _root_for(target)
    print(
        f"testgen: {len(files)} file(s) via {provider.name}:{provider.model}"
        f"{' [dry-run]' if args.dry_run else ''}\n"
    )

    written = failed = skipped = 0
    for src in files:
        result = generate_for_file(
            src,
            provider,
            root=root,
            output_dir=args.output_dir,
            description=args.description,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        rel_src = _relpath(src, root)
        if result.error:
            failed += 1
            print(f"  ✗ {rel_src}\n      {result.error}")
        elif result.written:
            written += 1
            print(f"  ✓ {rel_src}  ->  {_relpath(result.test_path, root)}")
        elif result.skipped_reason == "dry-run":
            skipped += 1
            print(f"  • {rel_src}  ->  {_relpath(result.test_path, root)}  (would write)")
        else:
            skipped += 1
            print(f"  – {rel_src}  ({result.skipped_reason})")

    print(f"\nDone. written={written} skipped={skipped} failed={failed}")
    return 1 if failed and not written else 0


def _relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
