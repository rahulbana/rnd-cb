"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/contentforge",
        description="Async SQLAlchemy database URL.",
    )

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key.")
    openai_model: str = Field(default="gpt-4o", description="Model used for writing/verifying.")
    openai_research_model: str = Field(
        default="gpt-4o-mini", description="Cheaper model used for trend research synthesis."
    )

    # Web search (deep search). Tavily is used when a key is present.
    tavily_api_key: str = Field(default="", description="Tavily API key for deep web search.")
    search_max_results: int = Field(default=8, description="Max results per web search call.")

    # App
    cors_origins: str = Field(default="*", description="Comma separated list of allowed origins.")
    request_timeout_seconds: int = Field(default=120)

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_tavily(self) -> bool:
        return bool(self.tavily_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
