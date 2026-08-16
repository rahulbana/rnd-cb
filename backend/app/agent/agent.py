"""Agentic RAG loop.

The model is given a set of tools (search_documents, get_current_time,
calculator, web_search) and decides which to call, iterating until it can
answer. Each tool call is streamed to the UI as a step in the thought-process
trace; retrieved passages surface as citations; the final answer is streamed.
"""
from __future__ import annotations

import json
import re
import time

from ..config import get_settings
from ..core.events import Phase, StepEmitter, bus
from ..core.logging import get_logger
from ..llm import get_llm
from ..tools.documents import SearchDocuments
from ..tools.registry import build_tools

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are an enterprise assistant with access to tools. Reason step by step "
    "and call tools when they help.\n"
    "- search_documents: the user's uploaded files — use it for anything that "
    "might be answered from their documents, and cite passages as [n].\n"
    "- calculator: any arithmetic or math.\n"
    "- get_current_time: the current date/time.\n"
    "- web_search: current, public information NOT in the user's documents.\n"
    "You may call multiple tools across steps. When you have enough information, "
    "give a concise, accurate answer, citing document passages as [n] where used. "
    "If the answer isn't available from tools or documents, say so plainly."
)


def _short_args(name: str, args: dict) -> str:
    for key in ("query", "expression", "timezone"):
        if key in args and args[key]:
            return str(args[key])[:80]
    return json.dumps(args)[:80] if args else ""


def _renumber(sources: list[dict]) -> list[dict]:
    out = []
    for i, s in enumerate(sources, 1):
        out.append({**s, "n": i})
    return out


async def run_agent(channel: str, query: str, options) -> None:
    settings = get_settings()
    emitter = StepEmitter(channel, Phase.CHAT)
    provider = getattr(options, "llm_provider", None) or settings.llm_provider

    try:
        llm = get_llm(provider)
        tools = build_tools(options, enabled=getattr(options, "tools_enabled", None))
        by_name = {t.name: t for t in tools}
        schemas = [t.schema() for t in tools]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        all_sources: list[dict] = []
        step_no = 0

        for _ in range(settings.agent_max_steps):
            t0 = time.perf_counter()
            turn = await llm.chat(messages, tools=schemas)
            think_dt = time.perf_counter() - t0

            if not turn.tool_calls:
                # Ready to answer.
                if all_sources:
                    await emitter.sources(_renumber(all_sources))
                await emitter.step_start("generate", f"Writing answer with {provider}")
                await _emit_answer(emitter, turn.content)
                await emitter.step_done("generate", f"model: {llm.model}",
                                        data={"seconds": round(think_dt, 3)})
                await emitter.step_done("complete", "done")
                await emitter.done()
                return

            # Record the assistant's tool-call request in history.
            messages.append({
                "role": "assistant",
                "content": turn.content or None,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name, "arguments": tc.arguments}}
                    for tc in turn.tool_calls
                ],
            })

            for tc in turn.tool_calls:
                step_no += 1
                sid = f"tool_{step_no}"
                tool = by_name.get(tc.name)
                try:
                    args = json.loads(tc.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                label = tool.label if tool else f"🔧 {tc.name}"
                await emitter.step_start(sid, _short_args(tc.name, args),
                                         data={"label": label})

                tt0 = time.perf_counter()
                if tool is None:
                    result = f"Unknown tool '{tc.name}'."
                else:
                    try:
                        result = await tool.run(**args)
                    except Exception as exc:  # noqa: BLE001
                        result = f"Tool error: {exc}"
                tool_dt = time.perf_counter() - tt0

                if isinstance(tool, SearchDocuments) and tool.last_sources:
                    all_sources.extend(tool.last_sources)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
                await emitter.step_done(sid, _truncate(result),
                                        data={"label": label, "seconds": round(tool_dt, 3)})

        # Step budget exhausted — force a final answer without tools.
        if all_sources:
            await emitter.sources(_renumber(all_sources))
        await emitter.step_start("generate", "Writing answer")
        final = await llm.chat(messages, tools=None)
        await _emit_answer(emitter, final.content)
        await emitter.step_done("generate", f"model: {llm.model}")
        await emitter.step_done("complete", "done")
        await emitter.done()
    except Exception as exc:  # noqa: BLE001
        log.exception("Agent failed")
        await emitter.error(f"Error: {exc}")
    finally:
        await bus.close(channel)


async def _emit_answer(emitter: StepEmitter, content: str) -> None:
    """Emit the final answer in small chunks for a progressive reveal."""
    if not content:
        await emitter.token("(no answer produced)")
        return
    parts = re.findall(r"\S+\s*|\s+", content)
    buf = ""
    for i, p in enumerate(parts):
        buf += p
        if (i + 1) % 3 == 0:
            await emitter.token(buf)
            buf = ""
    if buf:
        await emitter.token(buf)


def _truncate(text: str, n: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + "…"
