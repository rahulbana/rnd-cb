"""LangGraph node implementations for the deep-search agent.

Flow:  plan_queries -> search -> synthesize

Every node emits structured progress events through the EventEmitter found on
the RunnableConfig so the frontend can visualise the run live.
"""
from __future__ import annotations

import json
from typing import Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..config import settings
from ..events import get_emitter
from .state import AgentState, Source
from .tools import get_search_tool


def _llm(streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.2,
        streaming=streaming,
    )


PLANNER_SYSTEM = (
    "You are a research planner. Given a user's question, break it down into a "
    "set of focused, diverse web-search queries that together cover the topic "
    "comprehensively. Each query should explore a different angle, sub-topic, "
    "or perspective. Return ONLY a JSON array of strings, nothing else."
)


async def plan_queries(state: AgentState, config: RunnableConfig) -> Dict:
    """Use the LLM to expand the user query into multiple search queries."""
    emitter = get_emitter(config)
    query = state["query"]
    n = state.get("num_subqueries", settings.NUM_SUBQUERIES)

    if emitter:
        await emitter.emit(
            "node_start",
            node="plan_queries",
            label="Planning search strategy",
            detail=f"Decomposing the question into {n} sub-queries with the LLM.",
        )
        await emitter.emit("tool_call", tool="llm", model=settings.OPENAI_MODEL,
                           detail="Generating sub-queries")

    prompt = (
        f"User question: {query}\n\n"
        f"Generate exactly {n} distinct web-search queries as a JSON array."
    )
    resp = await _llm().ainvoke(
        [SystemMessage(content=PLANNER_SYSTEM), HumanMessage(content=prompt)]
    )

    subqueries = _parse_query_list(resp.content, fallback=query, n=n)

    if emitter:
        await emitter.emit("subqueries", subqueries=subqueries)
        await emitter.emit(
            "node_end",
            node="plan_queries",
            detail=f"Created {len(subqueries)} sub-queries.",
        )

    return {"subqueries": subqueries}


async def search(state: AgentState, config: RunnableConfig) -> Dict:
    """Run every sub-query through the web search tool and collect sources."""
    emitter = get_emitter(config)
    tool = get_search_tool()
    subqueries: List[str] = state["subqueries"]
    per_query = settings.RESULTS_PER_QUERY

    if emitter:
        await emitter.emit(
            "node_start",
            node="search",
            label="Searching the web",
            detail=f"Running {len(subqueries)} searches via '{tool.name}'.",
        )

    all_sources: List[Source] = []
    seen_urls = set()

    for idx, sq in enumerate(subqueries):
        if emitter:
            await emitter.emit(
                "tool_call",
                tool=tool.name,
                query=sq,
                index=idx,
                total=len(subqueries),
                detail=f"Searching: \"{sq}\"",
            )
        try:
            results = await tool.search(sq, per_query)
        except Exception as exc:  # surface search errors but keep going
            if emitter:
                await emitter.emit("tool_error", tool=tool.name, query=sq, error=str(exc))
            continue

        if emitter:
            await emitter.emit(
                "tool_result",
                tool=tool.name,
                query=sq,
                count=len(results),
                detail=f"Found {len(results)} results for \"{sq}\".",
            )

        for r in results:
            url = r.get("url", "")
            source: Source = {
                "title": r.get("title", "") or url,
                "url": url,
                "content": r.get("content", ""),
                "subquery": sq,
            }
            all_sources.append(source)
            if url and url not in seen_urls:
                seen_urls.add(url)
                if emitter:
                    await emitter.emit("source", source=source)

    if emitter:
        await emitter.emit(
            "node_end",
            node="search",
            detail=f"Collected {len(all_sources)} sources "
                   f"({len(seen_urls)} unique).",
        )

    return {"sources": all_sources}


SYNTH_SYSTEM = (
    "You are a meticulous research analyst. Using ONLY the provided search "
    "results, write a clear, well-structured answer to the user's question in "
    "Markdown. Cite sources inline using [n] notation that maps to the numbered "
    "sources. Be objective, note disagreements between sources, and do not "
    "invent facts that are not supported by the sources."
)


async def synthesize(state: AgentState, config: RunnableConfig) -> Dict:
    """Stream a final, cited report from the gathered sources."""
    emitter = get_emitter(config)
    query = state["query"]
    sources = state.get("sources", [])

    if emitter:
        await emitter.emit(
            "node_start",
            node="synthesize",
            label="Synthesizing report",
            detail="Writing a cited answer from the collected sources.",
        )
        await emitter.emit("tool_call", tool="llm", model=settings.OPENAI_MODEL,
                           detail="Generating final report")

    # Deduplicate sources by URL for citation numbering.
    numbered = _dedupe_sources(sources)
    context_blocks = []
    for i, s in enumerate(numbered, start=1):
        context_blocks.append(
            f"[{i}] {s['title']}\nURL: {s['url']}\n{s['content']}"
        )
    context = "\n\n".join(context_blocks) if context_blocks else "No results found."

    prompt = (
        f"User question: {query}\n\n"
        f"Numbered search results:\n\n{context}\n\n"
        "Write the answer now, citing sources as [n]. End with a short "
        "'## Sources' section listing each numbered source as a Markdown link."
    )

    report_parts: List[str] = []
    async for chunk in _llm(streaming=True).astream(
        [SystemMessage(content=SYNTH_SYSTEM), HumanMessage(content=prompt)]
    ):
        token = chunk.content or ""
        if token:
            report_parts.append(token)
            if emitter:
                await emitter.emit("token", text=token)

    report = "".join(report_parts)

    if emitter:
        await emitter.emit("node_end", node="synthesize", detail="Report complete.")
        await emitter.emit("report", report=report, sources=numbered)

    return {"report": report, "sources": numbered}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _parse_query_list(raw: str, fallback: str, n: int) -> List[str]:
    text = raw.strip()
    # Strip markdown code fences if the model wrapped the JSON.
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1] if "\n" in text else text
    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        data = json.loads(text[start:end])
        queries = [str(q).strip() for q in data if str(q).strip()]
        if queries:
            return queries[:n]
    except (ValueError, json.JSONDecodeError):
        pass
    # Fallback: split on newlines, else just use the original query.
    lines = [ln.strip("-* 1234567890.").strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln]
    return lines[:n] if lines else [fallback]


def _dedupe_sources(sources: List[Source]) -> List[Source]:
    seen = set()
    out: List[Source] = []
    for s in sources:
        url = s.get("url", "")
        key = url or s.get("title", "")
        if key and key not in seen:
            seen.add(key)
            out.append(s)
    return out
