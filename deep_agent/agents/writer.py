"""Writer Agent — composes the final, cited markdown report."""
from __future__ import annotations

from deep_agent.agents.base import BaseAgent
from deep_agent.config import get_settings
from deep_agent.models.schemas import (
    Citation,
    FactCheckResult,
    ReportStatus,
    ResearchReport,
)
from deep_agent.state import ResearchState
from deep_agent.utils.citations import validate_citations
from deep_agent.utils.context import build_sources_block

_SYSTEM = (
    "You are an expert research writer. Using ONLY the provided sources, "
    "write a comprehensive, well-structured markdown report that fulfils "
    "the objective. Requirements:\n"
    "- Start with a short executive summary.\n"
    "- Use clear ## / ### headings per sub-topic.\n"
    "- Support claims with inline numbered citations like [1], [2] that "
    "map to the numbered sources provided.\n"
    "- Be objective, precise and avoid speculation beyond the sources.\n"
    "- Note any material disagreements or gaps flagged by fact-checking.\n"
    "Do NOT invent a references section — it will be appended for you."
)

_USER = (
    "Topic: {topic}\n\n"
    "Objective:\n{objective}\n\n"
    "Numbered sources:\n{sources}\n\n"
    "Fact-check notes:\n{fact_checks}\n\n"
    "Write the full report body in markdown."
)


class WriterAgent(BaseAgent):
    """Synthesises all evidence into the final report."""

    name = "writer"

    def run(self, state: ResearchState) -> dict:
        plan = state["plan"]
        scraped = state.get("scraped", [])
        fact_checks: list[FactCheckResult] = state.get("fact_checks", [])

        # Budget the context; cite only the sources the model actually saw so
        # the references stay aligned with the evidence in the prompt.
        settings = get_settings()
        sources_block, included = build_sources_block(
            scraped,
            total_chars=settings.max_context_chars,
            per_source_chars=settings.per_source_chars,
        )
        if len(included) < len(scraped):
            self.logger.info(
                "Context budget: using %d of %d sources", len(included), len(scraped)
            )
        citations = [
            Citation(index=i + 1, title=doc.title or doc.url, url=doc.url)
            for i, doc in enumerate(included)
        ]

        fc_block = "\n".join(
            f"- ({fc.verdict.value}, conf={fc.confidence:.2f}) {fc.claim}"
            for fc in fact_checks
        ) or "(no fact-check notes)"

        self.logger.info(
            "Writing report from %d sources and %d fact-checks",
            len(scraped),
            len(fact_checks),
        )

        body = self._complete(
            system=_SYSTEM,
            user=_USER.format(
                topic=plan.topic,
                objective=plan.objective,
                sources=sources_block,
                fact_checks=fc_block,
            ),
        )

        # Post-pass: drop hallucinated citations, renumber the survivors and
        # rewrite the inline markers so the references section is trustworthy.
        validated = validate_citations(body, citations)
        self.logger.info(
            "Citations validated: %d cited, %d hallucinated dropped, "
            "%d provided sources unused",
            validated.referenced,
            validated.dangling_removed,
            validated.unused_dropped,
        )

        markdown = self._assemble(
            plan.topic, validated.body, validated.citations, fact_checks
        )
        report = ResearchReport(
            topic=plan.topic,
            markdown=markdown,
            status=ReportStatus.OK,
            citations=validated.citations,
        )
        self.logger.info("Report composed (%d chars)", len(markdown))
        return {"report": report}

    @staticmethod
    def _assemble(
        topic: str,
        body: str,
        citations: list[Citation],
        fact_checks: list[FactCheckResult],
    ) -> str:
        """Append a references section and fact-check appendix to the body."""

        parts = [f"# {topic}\n", body.strip(), "\n## References\n"]
        if citations:
            parts.extend(f"{c.index}. [{c.title}]({c.url})" for c in citations)
        else:
            parts.append("_No sources were cited in this report._")

        if fact_checks:
            parts.append("\n## Fact-Check Summary\n")
            parts.append("| Claim | Verdict | Confidence |")
            parts.append("| --- | --- | --- |")
            for fc in fact_checks:
                claim = fc.claim.replace("|", "\\|")
                parts.append(
                    f"| {claim} | {fc.verdict.value} | {fc.confidence:.2f} |"
                )

        return "\n".join(parts) + "\n"
