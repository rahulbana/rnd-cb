"""Configuration handling: environment loading and default review perspectives."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

from .reviewers import (
    Reviewer,
    all_reviewer_classes,
    reviewer_classes_by_key,
)

logger = logging.getLogger("code_review_agent")

# Config-file names auto-discovered in the working directory when no explicit
# --config path is provided.
CONFIG_FILENAMES = ("reviewers.yaml", "reviewers.yml", ".reviewers.yaml")

@dataclass
class Settings:
    """Runtime settings for a review run."""

    api_key: str
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 8192
    request_timeout: float = 90.0
    max_retries: int = 4
    concurrency: int = 4
    max_file_bytes: int = 400_000  # skip files larger than this
    chunk_lines: int = 400  # split larger files into chunks of this many lines
    resolve_dependencies: bool = True  # feed callee definitions to the reviewer
    max_dependency_defs: int = 12  # cap resolved definitions per file
    max_dependency_chars: int = 6000  # cap total dependency-context size
    max_index_files: int = 400  # cap files scanned when building the symbol index
    include_manifests: bool = True  # feed requirements/pyproject to the reviewer
    max_manifest_chars: int = 4000  # cap dependency-manifest context size
    static_checks: bool = True  # deterministic AST backstops (syntax, docstrings)
    reviewers: Optional[List[Reviewer]] = None

    def resolved_reviewers(self) -> List[Reviewer]:
        """Return the reviewers to run (all of them when none were selected)."""

        if self.reviewers is not None:
            return self.reviewers
        return [cls() for cls in all_reviewer_classes()]


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def discover_config_file(explicit: Optional[str]) -> Optional[str]:
    """Return the config path to use: the explicit one, or an auto-discovered one."""

    if explicit:
        if not os.path.isfile(explicit):
            raise ConfigError(f"Config file not found: {explicit}")
        return explicit
    for name in CONFIG_FILENAMES:
        if os.path.isfile(name):
            return name
    return None


def load_yaml_config(path: Optional[str]) -> Dict:
    """Load and lightly validate a YAML config file (returns {} when absent)."""

    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Could not read config file '{path}': {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"Config file '{path}' must be a mapping at the top level."
        )
    return data


def _reviewer_entry(value, default_enabled: bool) -> Tuple[bool, Optional[str]]:
    """Interpret a single ``reviewers:`` entry as ``(enabled, model_override)``.

    An entry may be a boolean (on/off) or a mapping such as
    ``{enabled: true, model: gpt-4o}`` to give that reviewer its own LLM model.
    """

    if isinstance(value, bool):
        return value, None
    if isinstance(value, dict):
        enabled = bool(value.get("enabled", True))
        model = value.get("model")
        return enabled, (str(model) if model else None)
    if value is None:
        return default_enabled, None
    return bool(value), None


def select_reviewers(reviewers_cfg: Optional[Dict]) -> List[Reviewer]:
    """Build the list of enabled :class:`Reviewer` instances from config.

    ``reviewers_cfg`` maps reviewer names to a boolean (on/off) or a mapping
    ``{enabled, model}``. A special ``default`` key sets the fallback for any
    reviewer not explicitly listed — so ``default: false`` plus ``syntax: true``
    runs only the syntax reviewer. Unknown reviewer names are ignored with a
    warning. When no mapping is given, every reviewer runs on the default model.
    """

    classes = all_reviewer_classes()
    if not reviewers_cfg:
        return [cls() for cls in classes]

    by_key = reviewer_classes_by_key()
    default_enabled = bool(reviewers_cfg.get("default", True))

    for name in sorted(set(reviewers_cfg) - set(by_key) - {"default"}):
        logger.warning("Ignoring unknown reviewer in config: '%s'", name)

    selected: List[Reviewer] = []
    for cls in classes:
        if cls.key in reviewers_cfg:
            enabled, model = _reviewer_entry(reviewers_cfg[cls.key], default_enabled)
        else:
            enabled, model = default_enabled, None
        if enabled:
            selected.append(cls(model=model))

    if not selected:
        raise ConfigError(
            "No reviewers are enabled. Enable at least one under 'reviewers:' "
            "in your config file."
        )
    return selected


def load_settings(
    env_file: Optional[str] = None,
    *,
    model: Optional[str] = None,
    concurrency: Optional[int] = None,
    config_file: Optional[str] = None,
) -> Settings:
    """Build :class:`Settings` from a ``.env`` file, environment, and YAML config.

    Environment variables (``.env`` or process env) that are honoured:

    * ``OPENAI_API_KEY``   (required)
    * ``OPENAI_MODEL``     (default ``gpt-4o-mini``)
    * ``OPENAI_BASE_URL``  (optional, for Azure/OpenAI-compatible gateways)
    * ``REVIEW_TEMPERATURE``, ``REVIEW_MAX_TOKENS``, ``REVIEW_TIMEOUT``,
      ``REVIEW_MAX_RETRIES``, ``REVIEW_CONCURRENCY``, ``REVIEW_MAX_FILE_BYTES``

    ``config_file`` (or an auto-discovered ``reviewers.yaml``) may enable/disable
    individual reviewers and override ``model`` and a few options. Precedence:
    explicit function arguments > YAML > environment > built-in defaults.
    """

    cfg = load_yaml_config(discover_config_file(config_file))
    reviewers_cfg = cfg.get("reviewers") if isinstance(cfg.get("reviewers"), dict) else None
    options = cfg.get("options") if isinstance(cfg.get("options"), dict) else {}
    reviewers = select_reviewers(reviewers_cfg)

    # ``load_dotenv`` will look for a .env in the CWD / parents when no path is
    # given. Existing process env vars take precedence (override=False).
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "OPENAI_API_KEY is not set. Create a .env file (see .env.example) "
            "or export the variable before running."
        )

    # Each ``_*`` helper resolves a value with precedence:
    # YAML options entry (``opt``) > environment variable > built-in default.
    def _float(opt: str, name: str, default: float) -> float:
        if opt in options:
            try:
                return float(options[opt])
            except (TypeError, ValueError):
                pass
        raw = os.getenv(name)
        try:
            return float(raw) if raw is not None else default
        except ValueError:
            return default

    def _int(opt: str, name: str, default: int) -> int:
        if opt in options:
            try:
                return int(options[opt])
            except (TypeError, ValueError):
                pass
        raw = os.getenv(name)
        try:
            return int(raw) if raw is not None else default
        except ValueError:
            return default

    def _bool(opt: str, name: str, default: bool) -> bool:
        if opt in options:
            return bool(options[opt])
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    model_final = (
        model
        or (str(cfg["model"]) if cfg.get("model") else None)
        or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )

    return Settings(
        api_key=api_key,
        model=model_final,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=_float("temperature", "REVIEW_TEMPERATURE", 0.0),
        max_tokens=_int("max_tokens", "REVIEW_MAX_TOKENS", 8192),
        request_timeout=_float("timeout", "REVIEW_TIMEOUT", 90.0),
        max_retries=_int("max_retries", "REVIEW_MAX_RETRIES", 4),
        concurrency=concurrency or _int("concurrency", "REVIEW_CONCURRENCY", 4),
        max_file_bytes=_int("max_file_bytes", "REVIEW_MAX_FILE_BYTES", 400_000),
        chunk_lines=_int("chunk_lines", "REVIEW_CHUNK_LINES", 400),
        resolve_dependencies=_bool("resolve_dependencies", "REVIEW_RESOLVE_DEPS", True),
        max_dependency_defs=_int("max_dependency_defs", "REVIEW_MAX_DEP_DEFS", 12),
        max_dependency_chars=_int("max_dependency_chars", "REVIEW_MAX_DEP_CHARS", 6000),
        max_index_files=_int("max_index_files", "REVIEW_MAX_INDEX_FILES", 400),
        include_manifests=_bool("include_manifests", "REVIEW_INCLUDE_MANIFESTS", True),
        max_manifest_chars=_int("max_manifest_chars", "REVIEW_MAX_MANIFEST_CHARS", 4000),
        static_checks=_bool("static_checks", "REVIEW_STATIC_CHECKS", True),
        reviewers=reviewers,
    )
