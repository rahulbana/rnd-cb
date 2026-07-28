"""Read node — fetch full text for the most credible unread sources.

Reading turns snippets into evidence: it fetches the page, strips markup to
plain text, and stores a bounded excerpt on the `Source`. We only read the top
sources by credibility to control latency and token cost; snippet-only sources
still contribute but are marked unread and weighted accordingly downstream.
"""

from __future__ import annotations

import asyncio
import re

import httpx
from langchain_core.runnables import RunnableConfig

from app.budget import BudgetTracker
from app.credibility import score_source
from app.graph.context import RuntimeContext
from app.graph.state import ResearchState
from app.models.schemas import JobStatus, ProgressEvent, Source

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_MAX_READ = 12          # cap sources read per iteration
_MAX_CHARS = 6000       # excerpt length stored per source


def _html_to_text(html: str) -> str:
    # Drop script/style blocks, then tags, then collapse whitespace.
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = _TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", text).strip()


async def _fetch(client: httpx.AsyncClient, src: Source) -> Source:
    try:
        resp = await client.get(src.url, follow_redirects=True)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "html" in ctype or "text" in ctype or not ctype:
            src.content = _html_to_text(resp.text)[:_MAX_CHARS]
            src.read = bool(src.content)
    except Exception:  # noqa: BLE001 — a page that won't load just stays snippet-only
        src.read = False
    if src.read:
        src.credibility = score_source(
            url=src.url,
            backend=src.backend,
            published=src.published,
            has_full_content=True,
        )
    return src


async def read_node(state: ResearchState, config: RunnableConfig) -> dict:
    ctx = RuntimeContext.from_config(config)
    budget: BudgetTracker = state["budget"]
    sources: list[Source] = state.get("sources", [])

    unread = [s for s in sources if not s.read and not s.content]
    unread.sort(key=lambda s: s.credibility, reverse=True)
    to_read = unread[:_MAX_READ]

    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="read",
            message=f"Reading full text of {len(to_read)} top sources…",
            iteration=budget.iterations,
            status=JobStatus.running,
        )
    )

    if to_read:
        async with httpx.AsyncClient(
            timeout=15.0, headers={"User-Agent": "DeepResearchAgent/0.1 (+research)"}
        ) as client:
            await asyncio.gather(*(_fetch(client, s) for s in to_read))

    read_count = sum(1 for s in to_read if s.read)
    ctx.emit_progress(
        ProgressEvent(
            job_id=ctx.job_id,
            phase="read",
            message=f"Extracted content from {read_count}/{len(to_read)} sources.",
            iteration=budget.iterations,
            sources_found=len(sources),
            usd_spent=budget.usd_spent,
        )
    )

    # Return the read sources; merge_sources reducer folds them back in by URL,
    # replacing the snippet-only copies with the now-read ones.
    return {"sources": to_read, "budget": budget}
