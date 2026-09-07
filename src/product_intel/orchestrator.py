"""Orchestrator / Director - the stateful graph that runs the agent pipeline.

Implements the topology from the architecture plan with a lightweight,
dependency-free director (no LangGraph/CrewAI required):

    Stage 1  Web Ingestion
        -> Stage 2  Sentiment & Topic Clustering
            -> Stage 3  (fan-out) Feature Audit  ||  Defect Diagnostics
                -> Stage 4  Roadmap & Backlog Synthesis

Every intermediate artifact is retained on the :class:`PipelineState` for
inspection, checkpointing and debugging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .agents import (
    DefectDiagnosticAgent,
    FeatureAuditAgent,
    RoadmapSynthesisAgent,
    SentimentTopicAgent,
    WebIngestionAgent,
)
from .agents.web_ingestion import Scraper
from .llm import get_llm
from .llm.base import LLMClient
from .schemas import (
    DefectLog,
    FeatureAuditReport,
    IngestedProduct,
    ProductReviewReport,
    SentimentReport,
)

ProgressHook = Callable[[str], None]


@dataclass
class PipelineState:
    """All artifacts produced along the run - the graph's checkpoint record."""

    url: str = ""
    ingested: Optional[IngestedProduct] = None
    sentiment: Optional[SentimentReport] = None
    audit: Optional[FeatureAuditReport] = None
    defects: Optional[DefectLog] = None
    report: Optional[ProductReviewReport] = None
    log: List[str] = field(default_factory=list)


class Orchestrator:
    def __init__(
        self,
        scraper: Optional[Scraper] = None,
        llm: Optional[LLMClient] = None,
        llm_provider: str = "offline",
        progress: Optional[ProgressHook] = None,
    ):
        self.llm = llm or get_llm(llm_provider)
        self.ingestion = WebIngestionAgent(scraper=scraper)
        self.sentiment_agent = SentimentTopicAgent()
        self.audit_agent = FeatureAuditAgent(self.llm)
        self.defect_agent = DefectDiagnosticAgent()
        self.roadmap_agent = RoadmapSynthesisAgent(self.llm)
        self._progress = progress

    def _emit(self, state: PipelineState, message: str) -> None:
        state.log.append(message)
        if self._progress:
            self._progress(message)

    def run(self, url: str = "") -> ProductReviewReport:
        state = self.run_stateful(url)
        assert state.report is not None
        return state.report

    def run_stateful(self, url: str = "") -> PipelineState:
        state = PipelineState(url=url)

        # -- Stage 1 -------------------------------------------------------- #
        self._emit(state, "Stage 1: Web ingestion & normalization")
        state.ingested = self.ingestion.run(url)
        self._emit(
            state,
            f"  ingested {len(state.ingested.reviews)} reviews for "
            f"'{state.ingested.metadata.name}'",
        )

        # -- Stage 2 -------------------------------------------------------- #
        self._emit(state, "Stage 2: Sentiment & topic clustering")
        state.sentiment = self.sentiment_agent.run(state.ingested)
        self._emit(
            state,
            f"  {len(state.sentiment.clusters)} clusters, "
            f"{state.sentiment.filtered_out} irrelevant reviews filtered",
        )

        # -- Stage 3 (fan-out) --------------------------------------------- #
        self._emit(state, "Stage 3: Feature audit || Defect diagnostics")
        state.audit = self.audit_agent.run(state.ingested.metadata, state.sentiment)
        state.defects = self.defect_agent.run(state.ingested)
        self._emit(
            state,
            f"  {len(state.audit.core_strengths)} strengths, "
            f"{len(state.audit.feature_gaps)} gaps, "
            f"{len(state.defects.defects)} distinct defects",
        )

        # -- Stage 4 -------------------------------------------------------- #
        self._emit(state, "Stage 4: Roadmap & backlog synthesis")
        backlog = self.roadmap_agent.run(
            state.defects.defects, state.audit, state.sentiment
        )
        self._emit(state, f"  {len(backlog)} backlog tickets generated")

        # -- Assemble final report ----------------------------------------- #
        meta = state.ingested.metadata
        product_summary = {
            "product_id": meta.product_id,
            "name": meta.name,
            "manufacturer": meta.manufacturer,
            "source_url": meta.source_url,
            "total_reviews_analyzed": state.sentiment.total_reviews_analyzed,
            "reviews_filtered_out": state.sentiment.filtered_out,
            "positive_sentiment_ratio": state.sentiment.positive_sentiment_ratio,
            "average_star_rating": state.sentiment.average_star_rating,
            "llm_provider": self.llm.name,
        }
        state.report = ProductReviewReport(
            product_summary=product_summary,
            core_strengths=state.audit.core_strengths,
            feature_gaps=state.audit.feature_gaps,
            vnext_backlog=backlog,
            clusters=state.sentiment.clusters,
            defects=state.defects.defects,
        )
        self._emit(state, "Done.")
        return state
