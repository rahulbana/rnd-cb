"""Backend configuration loaded from the environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the API backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- OpenAI -------------------------------------------------------------
    openai_api_key: str = Field(..., description="OpenAI API key.")
    openai_model: str = Field(default="gpt-4o-mini", description="Chat model id.")
    openai_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # --- Remote MCP server --------------------------------------------------
    mcp_server_url: str = Field(
        default="http://localhost:8100/mcp",
        description="Streamable-HTTP endpoint of the remote MCP server.",
    )
    mcp_transport: str = Field(default="streamable_http")

    # --- Agent behaviour ----------------------------------------------------
    system_prompt: str = Field(
        default=(
            "You are Reel, a friendly and knowledgeable movie concierge. You help "
            "users discover films, learn about cast and crew, and answer practical "
            "questions using your tools.\n\n"
            "Guidelines:\n"
            "- Use the TMDB tools for anything about movies, TV, actors, or ratings. "
            "Never invent movie facts, ids, or ratings — look them up.\n"
            "- To filter by genre, first call list_movie_genres to resolve names to ids.\n"
            "- Use the translate tool when a user asks to translate text.\n"
            "- Use the time tools for questions about the current time, timezones, or "
            "converting times between countries.\n"
            "- Be concise, cite concrete details (year, rating, director) when relevant, "
            "and format lists with markdown. When you show a movie, include its rating "
            "and release year if available."
        ),
        description="System prompt seeding the agent's persona and policy.",
    )

    # --- HTTP / CORS --------------------------------------------------------
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Origins allowed to call the API (the React dev server).",
    )
    request_timeout_seconds: float = Field(default=90.0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
