"""Application configuration loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the CSV Insight Agent."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenAI configuration. When the key is empty the agent falls back to a
    # deterministic, rule-based narrative so the app still works offline.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    # Upload guardrails.
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB
    max_rows_for_llm: int = 50  # sample size handed to the LLM as context

    # CORS — comma separated list of allowed origins for the React dev server.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
