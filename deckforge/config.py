"""Centralised, environment-driven configuration.

Everything tunable lives here so the rest of the codebase never reaches for
``os.environ`` directly. Values resolve from a local ``.env`` file or the
process environment (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Credentials ---
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    # --- Models ---
    model: str = Field(default="gpt-4o", alias="DECKFORGE_MODEL")
    fast_model: str = Field(default="gpt-4o-mini", alias="DECKFORGE_FAST_MODEL")
    temperature: float = Field(default=0.6, alias="DECKFORGE_TEMPERATURE")

    # --- Research ---
    max_searches: int = Field(default=4, alias="DECKFORGE_MAX_SEARCHES")

    # --- Output ---
    theme: str = Field(default="midnight", alias="DECKFORGE_THEME")
    output_dir: Path = Field(default=Path("ppt"), alias="DECKFORGE_OUTPUT_DIR")

    @property
    def research_enabled(self) -> bool:
        """Web research only runs when a Tavily key is present."""
        return bool(self.tavily_api_key.strip())

    def require_openai(self) -> str:
        """Return the OpenAI key or raise a clear, actionable error."""
        if not self.openai_api_key.strip():
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add "
                "your key, or export OPENAI_API_KEY in your shell."
            )
        return self.openai_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor so settings are parsed exactly once per process."""
    return Settings()  # type: ignore[call-arg]
