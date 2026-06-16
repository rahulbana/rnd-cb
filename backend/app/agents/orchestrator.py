"""Orchestrator: wires the agents into the end-to-end pipeline.

Flow:
    SearchAgent -> SummaryAgent + ReviewAgent -> VerifierAgent -> BookReport
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import BookReport
from ..web_search import WebSearchClient
from .review_agent import ReviewAgent
from .search_agent import SearchAgent
from .summary_agent import SummaryAgent
from .verifier_agent import VerifierAgent


class Orchestrator:
    def __init__(
        self,
        llm: LLMClient | None = None,
        search_client: WebSearchClient | None = None,
    ) -> None:
        llm = llm or LLMClient()
        self.search_agent = SearchAgent(search_client)
        self.summary_agent = SummaryAgent(llm)
        self.review_agent = ReviewAgent(llm)
        self.verifier_agent = VerifierAgent(llm)

    def run(self, title: str, author: str | None = None) -> BookReport:
        sources = self.search_agent.run(title, author)

        book = self.summary_agent.run(title, sources, author_hint=author)
        reviews = self.review_agent.run(title, sources)
        verification = self.verifier_agent.run(book, reviews, sources)

        return BookReport(
            book=book,
            reviews=reviews,
            verification=verification,
            sources=[s.url for s in sources if s.url],
        )
