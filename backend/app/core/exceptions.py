"""Application exception hierarchy.

Each ``AppError`` carries an HTTP status code and a stable ``error_type`` so the
API can translate it into a consistent JSON error envelope.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code: int = 500
    error_type: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(AppError):
    """A required configuration value (e.g. an API key) is missing."""

    status_code = 503
    error_type = "configuration_error"


class LLMError(AppError):
    """The language model call failed."""

    status_code = 502
    error_type = "llm_error"


class PlanGenerationError(AppError):
    """The agent workflow failed to produce a plan."""

    status_code = 502
    error_type = "plan_generation_error"


class ExportError(AppError):
    """Rendering a plan to an export format failed."""

    status_code = 500
    error_type = "export_error"
