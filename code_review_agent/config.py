"""Configuration handling: environment loading and default review perspectives."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv

from .models import ReviewCategory

logger = logging.getLogger("code_review_agent")

# Config-file names auto-discovered in the working directory when no explicit
# --config path is provided.
CONFIG_FILENAMES = ("reviewers.yaml", "reviewers.yml", ".reviewers.yaml")

# ---------------------------------------------------------------------------
# Review perspectives
# ---------------------------------------------------------------------------
# These are the "perspectives" the agent inspects. The list is intentionally
# data-driven so it is trivial to extend without touching the review engine.
DEFAULT_CATEGORIES: List[ReviewCategory] = [
    ReviewCategory(
        key="syntax",
        title="Syntax Review",
        guidance=(
            "Check for: syntax errors; invalid or inconsistent indentation; "
            "missing imports (names used but never imported); circular "
            "imports; unused imports; duplicate imports; invalid or misapplied "
            "decorators."
        ),
    ),
    ReviewCategory(
        key="error_handling",
        title="Error Handling",
        guidance=(
            "Check for: missing try/except around fallible operations; try "
            "blocks that are too large or wrap unrelated code; swallowed "
            "exceptions (caught then ignored); bare `except:`; incorrect "
            "exception hierarchy ordering; raising generic `Exception`; "
            "missing `finally`; missing cleanup of resources on error paths; "
            "incorrect re-raise (losing the original traceback, e.g. `raise e` "
            "vs bare `raise`)."
        ),
    ),
    ReviewCategory(
        key="exception_handling",
        title="Exception Handling",
        guidance=(
            "Check that exceptions are specific rather than broad; that custom "
            "exception types are defined and used where appropriate; and that "
            "exception chaining (`raise ... from ...`) is used to preserve "
            "context."
        ),
    ),
    ReviewCategory(
        key="type_safety",
        title="Type Safety",
        guidance=(
            "Check for missing type hints on functions, parameters, returns "
            "and important variables. Using the DEPENDENCY DEFINITIONS block "
            "when present, flag calls whose argument or return types are "
            "inconsistent with the callee's signature."
        ),
    ),
    ReviewCategory(
        key="data_validation",
        title="Data Validation",
        guidance=(
            "Check for: missing None checks; missing empty-string checks; "
            "missing input validation on external/user data; missing schema "
            "validation; where an Enum would be safer than magic strings; and "
            "missing dataclass/`__post_init__` validation."
        ),
    ),
    ReviewCategory(
        key="best_practices",
        title="Python Best Practices",
        guidance=(
            "Check adherence to: PEP 8 (style) and PEP 257 (docstrings); "
            "naming conventions; avoiding magic numbers; using list "
            "comprehensions, context managers, generators, `enumerate`, `zip`, "
            "the walrus operator, `match`-`case`, and f-strings where they "
            "make the code clearer and more idiomatic."
        ),
    ),
    ReviewCategory(
        key="performance",
        title="Performance Review",
        guidance=(
            "Check for: nested loops with poor complexity; repeated DB calls "
            "(N+1); repeated API calls; regex compiled inside loops instead of "
            "once; large memory allocations; costly sorting; repeated object "
            "creation; inefficient string concatenation in loops; repeated "
            "JSON parsing; and repeatedly opening the same file."
        ),
    ),
    ReviewCategory(
        key="memory",
        title="Memory Review",
        guidance=(
            "Check for: unnecessarily large lists (use generators); memory "
            "leaks; cache misuse (unbounded caches); reference cycles; overuse "
            "of global variables; huge dictionaries; and copying data instead "
            "of using a view/slice/iterator."
        ),
    ),
    ReviewCategory(
        key="resource_management",
        title="Resource Management",
        guidance=(
            "Check that files, database handles, network connections, sockets "
            "and threads are always released: prefer context managers (`with`) "
            "over manual close, ensure cleanup on every path, and verify "
            "threads/pools are joined or shut down."
        ),
    ),
    ReviewCategory(
        key="security",
        title="Security Review",
        guidance=(
            "Check for: SQL injection; command injection; path traversal; "
            "unsafe `pickle`; unsafe `yaml.load`; hardcoded passwords or API "
            "keys; weak hashing (MD5/SHA1 for secrets); `random` instead of "
            "`secrets`; missing JWT validation; missing authentication or "
            "authorization; CSRF; XSS; SSRF; open redirect; insecure "
            "deserialization; unsafe `eval()`/`exec()`; `subprocess(..., "
            "shell=True)`; insecure temp-file creation; and overly permissive "
            "file permissions."
        ),
    ),
    ReviewCategory(
        key="code_quality",
        title="Code Quality",
        guidance=(
            "Check for: duplicate code; overly long methods; overly long "
            "classes; dead code; unused variables; unused methods; deep "
            "nesting; high cyclomatic complexity; and general code smells."
        ),
    ),
    ReviewCategory(
        key="readability",
        title="Readability",
        guidance=(
            "Check: clear naming; reasonable function and class length; "
            "descriptive variable names; and boolean names that read as "
            "predicates (`is_`, `has_`, `should_`)."
        ),
    ),
    ReviewCategory(
        key="documentation",
        title="Documentation",
        guidance=(
            "Every module, class, method and function MUST have a docstring. "
            "Treat a missing docstring as a definite issue (status = 1) and "
            "emit one issue per undocumented symbol. This is an objective, "
            "non-negotiable check: report it even for short, trivial, "
            "one-line, or self-explanatory functions, for private/helper "
            "functions, and for the module-level docstring at the very top of "
            "the file. Do NOT skip a missing docstring on the grounds that the "
            "code is simple or obvious. Docstrings should follow PEP 257 "
            "(imperative one-line summary, blank line before any longer body) "
            "and, where the symbol takes parameters, returns a value, or raises "
            "exceptions, document them (Args/Returns/Raises or an equivalent "
            "style). Also flag empty, placeholder ('TODO'), or stale docstrings "
            "that no longer match the code, non-obvious logic that lacks "
            "explanatory comments, and comments that are misleading or "
            "redundant. When suggesting a fix, provide the exact docstring or "
            "comment text to add."
        ),
    ),
    ReviewCategory(
        key="dependency",
        title="Dependency Review",
        guidance=(
            "Using the PROJECT DEPENDENCIES manifest block when present, check "
            "for: packages imported but not declared, and packages declared "
            "but unused; outdated packages; known CVEs / vulnerable versions "
            "(based on your knowledge — say so if unsure); duplicate packages; "
            "version conflicts; and requirements.txt hygiene (unpinned or "
            "loosely pinned versions). Do not fabricate CVE identifiers."
        ),
    ),
]


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
    categories: Optional[List[ReviewCategory]] = None

    def resolved_categories(self) -> List[ReviewCategory]:
        return self.categories or DEFAULT_CATEGORIES


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


def select_categories(reviewers_cfg: Optional[Dict]) -> List[ReviewCategory]:
    """Filter the default perspectives by a ``reviewers`` on/off mapping.

    The mapping keys are reviewer names; values are booleans. A special
    ``default`` key sets the fallback for any reviewer not explicitly listed
    (so ``default: false`` plus ``syntax: true`` runs only the syntax reviewer).
    Unknown reviewer names are ignored with a warning. When no mapping is given,
    every reviewer is enabled.
    """

    if not reviewers_cfg:
        return list(DEFAULT_CATEGORIES)

    valid = {c.key for c in DEFAULT_CATEGORIES}
    default_enabled = bool(reviewers_cfg.get("default", True))

    unknown = set(reviewers_cfg) - valid - {"default"}
    for name in sorted(unknown):
        logger.warning("Ignoring unknown reviewer in config: '%s'", name)

    selected = [
        c
        for c in DEFAULT_CATEGORIES
        if bool(reviewers_cfg.get(c.key, default_enabled))
    ]
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
    categories = select_categories(reviewers_cfg)

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
        categories=categories,
    )
