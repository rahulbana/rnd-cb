"""Extractor agent: turn a URL or raw text into a clean :class:`Article`.

The heavy lifting (HTML download + boilerplate removal) is done by the
``trafilatura`` library. The LLM is used only as a light cleanup / titling
pass so that downstream agents get tidy, well-titled content.
"""

from __future__ import annotations

import logging

from ..models import Article
from .base import LLMAgent

logger = logging.getLogger("podcastify")


class _Meta(LLMAgent):
    """Internal helper schema is defined inline to keep imports simple."""


class ExtractorAgent(LLMAgent):
    name = "extractor"
    system_prompt = (
        "You are a meticulous content editor. You are given the raw text of "
        "an article or blog post. Clean it up: remove navigation, ads, cookie "
        "notices, social-share prompts and any other boilerplate, while "
        "preserving the full substance of the piece. Do not summarise or "
        "shorten the ideas — only strip noise. Return the cleaned article body "
        "as plain text."
    )

    def extract(self, *, url: str | None = None, text: str | None = None) -> Article:
        """Build an :class:`Article` from a URL or raw text.

        Exactly one of ``url`` or ``text`` should be provided.
        """
        if not url and not text:
            raise ValueError("Provide either a url or text to extract.")

        raw_title: str | None = None
        raw_author: str | None = None
        source_url = url

        if url:
            raw_text, raw_title, raw_author = self._fetch(url)
        else:
            raw_text = text or ""

        if not raw_text.strip():
            raise RuntimeError("No readable content was found to convert.")

        # Light LLM cleanup pass (skipped for already-clean short text would
        # still be cheap, so we always run it for consistency).
        cleaned = self.complete(
            "Clean the following article text. Return only the cleaned body:\n\n"
            + raw_text[:24000]
        )

        title = raw_title or self._title_for(cleaned)
        return Article(
            title=title.strip() or "Untitled",
            author=raw_author,
            source_url=source_url,
            text=cleaned.strip() or raw_text.strip(),
        )

    # -- internals ----------------------------------------------------------

    def _fetch(self, url: str) -> tuple[str, str | None, str | None]:
        """Download and extract the main content from a URL."""
        self._log(f"fetching {url}")
        try:
            import trafilatura
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "trafilatura is required to fetch URLs. `pip install trafilatura`"
            ) from exc

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise RuntimeError(f"Could not download {url}")

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
        )
        title = None
        author = None
        try:
            meta = trafilatura.extract_metadata(downloaded)
            if meta:
                title = meta.title
                author = meta.author
        except Exception:  # pragma: no cover - metadata is best-effort
            pass

        if not text:
            raise RuntimeError(f"Could not extract readable text from {url}")
        return text, title, author

    def _title_for(self, text: str) -> str:
        """Ask the LLM for a concise title when one is not available."""
        return self.complete(
            "Give a short, descriptive title (max 10 words) for this article. "
            "Return only the title, no quotes:\n\n" + text[:4000]
        )
