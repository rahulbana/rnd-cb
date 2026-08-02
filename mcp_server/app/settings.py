"""Runtime configuration for the MCP server.

All values are sourced from environment variables (optionally a local ``.env``
file) so the same image can be deployed across environments without code
changes.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MCP_",
        extra="ignore",
    )

    # --- Server binding -----------------------------------------------------
    host: str = Field(default="0.0.0.0", description="Interface to bind to.")
    port: int = Field(default=8100, description="Port for the streamable-HTTP transport.")

    # DNS-rebinding protection guards *browser-originated* requests. This server
    # is an internal tool endpoint reached by the trusted backend over the
    # network, where the Host header varies by deployment (localhost, a Docker
    # service name, etc.), so we disable the host check by default. Set to False
    # and populate ``allowed_hosts`` if you expose it to untrusted clients.
    disable_host_check: bool = Field(default=True)
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost:*", "127.0.0.1:*"],
        description="Host allow-list (with :* port wildcards) when host check is enabled.",
    )

    # --- TMDB ---------------------------------------------------------------
    # Either a v4 read-access token (preferred, sent as a Bearer token) or a
    # legacy v3 API key can be supplied. The TMDB client picks whichever is set.
    tmdb_api_key: str | None = Field(default=None, description="TMDB v3 API key.")
    tmdb_read_access_token: str | None = Field(
        default=None, description="TMDB v4 read access token (Bearer)."
    )
    tmdb_base_url: str = Field(default="https://api.themoviedb.org/3")
    tmdb_image_base_url: str = Field(default="https://image.tmdb.org/t/p")
    tmdb_timeout_seconds: float = Field(default=15.0)

    @property
    def tmdb_configured(self) -> bool:
        return bool(self.tmdb_api_key or self.tmdb_read_access_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
