"""Core orchestration: source file -> LLM -> written test file."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import languages, prompts
from .llm import LLMProvider

# Skip anything absurdly large to avoid blowing the context window.
MAX_SOURCE_CHARS = 60_000


@dataclass
class GenResult:
    source: Path
    test_path: Path
    written: bool
    skipped_reason: str | None = None
    error: str | None = None


def _strip_code_fences(text: str) -> str:
    """Remove ```lang ... ``` fences the model may add despite instructions."""
    text = text.strip()
    fence = re.match(r"^```[a-zA-Z0-9_+-]*\n(.*)\n```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip() + "\n"
    # Fallback: drop any stray fence lines.
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
    return "\n".join(lines).strip() + "\n"


def _module_hint(source: Path, root: Path) -> str:
    """A human/LLM-friendly reference to the file under test."""
    try:
        rel = source.resolve().relative_to(root.resolve())
    except ValueError:
        rel = Path(source.name)
    return rel.as_posix()


def _resolve_test_path(
    source: Path,
    spec: languages.LanguageSpec,
    root: Path,
    output_dir: Path | None,
) -> Path:
    test_name = spec.test_filename(source)
    if output_dir is not None:
        # Mirror the source tree under the output dir to avoid collisions.
        try:
            rel_parent = source.resolve().parent.relative_to(root.resolve())
        except ValueError:
            rel_parent = Path()
        return (output_dir / rel_parent / test_name).resolve()
    # Default: place the test alongside the source file.
    return (source.parent / test_name).resolve()


def generate_for_file(
    source: Path,
    provider: LLMProvider,
    *,
    root: Path,
    output_dir: Path | None = None,
    description: str | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> GenResult:
    """Generate (and optionally write) a test file for a single source file."""
    spec = languages.detect(source)
    if spec is None:
        return GenResult(source, source, False, skipped_reason="unsupported language")

    test_path = _resolve_test_path(source, spec, root, output_dir)
    if test_path.exists() and not overwrite and not dry_run:
        return GenResult(source, test_path, False, skipped_reason="test exists (use --overwrite)")

    try:
        code = source.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return GenResult(source, test_path, False, error=f"cannot read source: {exc}")

    if not code.strip():
        return GenResult(source, test_path, False, skipped_reason="empty file")
    if len(code) > MAX_SOURCE_CHARS:
        return GenResult(source, test_path, False, skipped_reason="file too large")

    user_prompt = prompts.build_user_prompt(
        spec=spec,
        source_code=code,
        module_hint=_module_hint(source, root),
        description=description,
    )

    try:
        raw = provider.complete(prompts.SYSTEM_PROMPT, user_prompt)
    except Exception as exc:  # provider raises LLMError; be defensive
        return GenResult(source, test_path, False, error=str(exc))

    content = _strip_code_fences(raw)
    if not content.strip():
        return GenResult(source, test_path, False, error="model returned no test code")

    if dry_run:
        return GenResult(source, test_path, False, skipped_reason="dry-run")

    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(content, encoding="utf-8")
    return GenResult(source, test_path, True)
