"""Application-specific exception hierarchy."""
from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors."""

    status_code: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(AppError):
    """Raised when the app is misconfigured (e.g. missing API key)."""

    status_code = 500


class ProviderError(AppError):
    """Base for provider (LLM / search) failures."""

    status_code = 502


class LLMProviderError(ProviderError):
    pass


class SearchProviderError(ProviderError):
    pass
