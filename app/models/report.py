"""Structured report models — the analyst-grade deliverable.

These models are used both as the LLM's structured-output schema (via
`with_structured_output`) and as the validated object the API returns and the
exporters render. Keeping citations as first-class objects lets us render
numbered references and verify that every claim maps to a real source.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Citation(BaseModel):
    """A numbered citation resolvable back to a `Source`."""

    number: int = Field(..., ge=1, description="1-based citation index used inline as [n].")
    source_id: str
    title: str
    url: str
    credibility: float = Field(default=0.5, ge=0.0, le=1.0)


class ReportTable(BaseModel):
    """A comparison/data table embedded in a section."""

    title: str
    columns: list[str]
    rows: list[list[str]]

    @model_validator(mode="after")
    def _check_shape(self) -> ReportTable:
        width = len(self.columns)
        for i, row in enumerate(self.rows):
            if len(row) != width:
                raise ValueError(
                    f"table '{self.title}' row {i} has {len(row)} cells, expected {width}"
                )
        return self

    def to_markdown(self) -> str:
        header = "| " + " | ".join(self.columns) + " |"
        sep = "| " + " | ".join("---" for _ in self.columns) + " |"
        body = "\n".join("| " + " | ".join(r) + " |" for r in self.rows)
        return "\n".join([header, sep, body])


class ReportSection(BaseModel):
    """A titled body section. Inline citations use [n] referencing `Citation.number`."""

    heading: str
    body: str = Field(..., description="Markdown prose with inline [n] citation markers.")
    tables: list[ReportTable] = Field(default_factory=list)
    citation_numbers: list[int] = Field(
        default_factory=list,
        description="Citation numbers referenced in this section (for validation).",
    )


class ResearchReport(BaseModel):
    """The full validated report object."""

    title: str
    topic: str
    executive_summary: str = Field(..., min_length=50)
    key_findings: list[str] = Field(default_factory=list, description="Bulletized takeaways.")
    sections: list[ReportSection]
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Model's self-assessed confidence."
    )
    open_questions: list[str] = Field(
        default_factory=list, description="Gaps that remained unresolved within budget."
    )

    @model_validator(mode="after")
    def _citations_are_contiguous(self) -> ResearchReport:
        if self.citations:
            numbers = sorted(c.number for c in self.citations)
            expected = list(range(1, len(numbers) + 1))
            if numbers != expected:
                raise ValueError(
                    f"citation numbers must be contiguous 1..N, got {numbers}"
                )
        return self

    def to_markdown(self) -> str:
        """Render the full report as an analyst-grade Markdown document."""
        parts: list[str] = [f"# {self.title}\n"]
        parts.append(f"_Topic: {self.topic}_  ·  _Confidence: {self.confidence:.0%}_\n")

        parts.append("## Executive Summary\n")
        parts.append(self.executive_summary + "\n")

        if self.key_findings:
            parts.append("## Key Findings\n")
            parts.extend(f"- {kf}" for kf in self.key_findings)
            parts.append("")

        for sec in self.sections:
            parts.append(f"## {sec.heading}\n")
            parts.append(sec.body + "\n")
            for tbl in sec.tables:
                parts.append(f"**{tbl.title}**\n")
                parts.append(tbl.to_markdown() + "\n")

        if self.open_questions:
            parts.append("## Open Questions & Gaps\n")
            parts.extend(f"- {q}" for q in self.open_questions)
            parts.append("")

        if self.citations:
            parts.append("## References\n")
            for c in sorted(self.citations, key=lambda x: x.number):
                parts.append(f"{c.number}. [{c.title}]({c.url})")
            parts.append("")

        return "\n".join(parts)
