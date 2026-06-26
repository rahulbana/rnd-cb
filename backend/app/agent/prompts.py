"""Centralised prompt templates for the agent nodes."""
from __future__ import annotations

from typing import List

from ..schemas.source import Source

PLANNER_SYSTEM = (
    "You are a research planner. Given a user's question, break it down into a "
    "set of focused, diverse web-search queries that together cover the topic "
    "comprehensively. Each query should explore a different angle, sub-topic, "
    "or perspective. Return ONLY a JSON array of strings, nothing else."
)

SYNTH_SYSTEM = (
    "You are a meticulous research analyst. Using ONLY the provided search "
    "results, write a comprehensive, in-depth answer to the user's question in "
    "Markdown. Be thorough: organise the report with a short introduction, "
    "multiple '##' sections covering each major sub-topic in detail, and a brief "
    "conclusion. Explain context, nuances, and trade-offs rather than just "
    "listing facts. Cite sources inline using [n] notation that maps to the "
    "numbered sources. Be objective, note disagreements between sources, and do "
    "not invent facts that are not supported by the sources."
)


def planner_prompt(query: str, n: int) -> str:
    return (
        f"User question: {query}\n\n"
        f"Generate exactly {n} distinct web-search queries as a JSON array."
    )


def synthesis_prompt(
    query: str, sources: List[Source], target_words: int, content_chars: int
) -> str:
    if sources:
        blocks = [
            f"[{i}] {s.title}\nURL: {s.url}\n{(s.content or '')[:content_chars]}"
            for i, s in enumerate(sources, start=1)
        ]
        context = "\n\n".join(blocks)
    else:
        context = "No results found."

    return (
        f"User question: {query}\n\n"
        f"Numbered search results:\n\n{context}\n\n"
        f"Write a detailed, comprehensive answer of roughly {target_words} words "
        "(longer if the topic warrants it). Use multiple Markdown sections and "
        "cite sources as [n] throughout. End with a '## Sources' section listing "
        "each numbered source as a Markdown link."
    )
