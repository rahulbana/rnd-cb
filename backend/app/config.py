"""Application configuration loaded from environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Web search
    # If TAVILY_API_KEY is set we use Tavily, otherwise we fall back to
    # DuckDuckGo which requires no API key (great for local dev / demos).
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "auto")  # auto|tavily|duckduckgo

    # Agent behaviour
    NUM_SUBQUERIES: int = int(os.getenv("NUM_SUBQUERIES", "4"))
    RESULTS_PER_QUERY: int = int(os.getenv("RESULTS_PER_QUERY", "4"))

    # Length / depth of the synthesized report
    # Max output tokens the synthesis LLM may produce for the report.
    REPORT_MAX_TOKENS: int = int(os.getenv("REPORT_MAX_TOKENS", "4000"))
    # Rough target length the model is asked to aim for (in words).
    REPORT_TARGET_WORDS: int = int(os.getenv("REPORT_TARGET_WORDS", "800"))
    # Max characters of each source's content fed into the synthesis prompt.
    SOURCE_CONTENT_CHARS: int = int(os.getenv("SOURCE_CONTENT_CHARS", "2000"))

    # CORS
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "*")


settings = Settings()
