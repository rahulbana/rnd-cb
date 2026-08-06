"""The agent: an OpenAI tool-calling loop over the registered tools."""
from __future__ import annotations

import json
from datetime import date
from typing import Iterator

from ..config import config
from ..logging_config import get_logger
from ..tools import build_registry
from .client import LLMUnavailable, get_client

logger = get_logger("agent")

SYSTEM_PROMPT = (
    "You are a helpful, multi-tool desktop assistant. You have access to a set "
    "of tools for web search, weather, air quality, country facts, time, "
    "currency and unit conversion, system health, translation, summarization, "
    "fact-checking, note management, historical events, festival dates, image "
    "resizing, news, public holidays, age calculation and saving research to "
    "files.\n\n"
    "Guidelines:\n"
    "- Use tools whenever they can provide accurate, up-to-date, or computed "
    "information instead of guessing.\n"
    "- You may call multiple tools, in sequence, to fully answer a request.\n"
    "- After using tools, give a clear, concise natural-language answer.\n"
    "- If a tool returns an error, explain it plainly and suggest a fix.\n"
    f"- Today's date is {date.today().isoformat()}."
)

MAX_ITERATIONS = 8


def _result_file_path(result) -> str | None:
    """Return a filesystem path a tool produced, if any (for UI file actions)."""
    if not isinstance(result, dict) or not result.get("ok", False):
        return None
    data = result.get("data")
    if not isinstance(data, dict):
        return None
    # save_research -> "path"; resize_image -> "output".
    return data.get("path") or data.get("output")


class Agent:
    """Stateless-per-call agent that runs the tool-calling loop."""

    def __init__(self) -> None:
        self.registry = build_registry()
        self.tool_schemas = [t.openai_schema() for t in self.registry.values()]

    def _execute_tool(self, name: str, arguments: str) -> tuple[dict, dict]:
        """Run a tool and return (result, trace_entry)."""
        tool = self.registry.get(name)
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            args = {}
        if tool is None:
            logger.warning("Agent requested unknown tool '%s'", name)
            result = {"ok": False, "error": f"Unknown tool '{name}'."}
        else:
            try:
                logger.info("Tool call: %s(%s)", name, args)
                result = tool.run(**args)
            except Exception as exc:  # tools shouldn't raise, but be safe
                logger.exception("Tool '%s' raised an exception (args=%s)", name, args)
                result = {"ok": False, "error": f"Tool '{name}' failed: {exc}"}
        ok_flag = bool(isinstance(result, dict) and result.get("ok", True))
        if not ok_flag:
            error_msg = result.get("error") if isinstance(result, dict) else result
            logger.error("Tool '%s' returned an error: %s", name, error_msg)
        trace = {"tool": name, "arguments": args, "ok": ok_flag}
        file_path = _result_file_path(result)
        if file_path:
            trace["file"] = file_path
        return result, trace

    def chat(self, messages: list[dict]) -> dict:
        """Run one assistant turn over the given conversation history.

        `messages` is a list of {role, content} dicts. Returns a dict with the
        assistant reply and a trace of any tools invoked.
        """
        try:
            client = get_client()
        except LLMUnavailable as exc:
            return {"reply": str(exc), "tools_used": [], "ok": False}

        convo = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        trace: list[dict] = []

        for _ in range(MAX_ITERATIONS):
            try:
                resp = client.chat.completions.create(
                    model=config.active_model(),
                    messages=convo,
                    tools=self.tool_schemas,
                    tool_choice="auto",
                    temperature=0.3,
                )
            except Exception as exc:
                logger.exception("LLM request failed")
                return {"reply": f"LLM request failed: {exc}",
                        "tools_used": trace, "ok": False}
            msg = resp.choices[0].message

            if not msg.tool_calls:
                return {"reply": msg.content or "", "tools_used": trace, "ok": True}

            # Append the assistant's tool-call message, then each tool result.
            convo.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                result, entry = self._execute_tool(tc.function.name, tc.function.arguments)
                trace.append(entry)
                convo.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str)[:8000],
                })

        return {
            "reply": "I reached the maximum number of tool steps for this request. "
                     "Here is what I gathered so far — please refine your question.",
            "tools_used": trace,
            "ok": True,
        }

    def chat_stream(self, messages: list[dict]) -> Iterator[dict]:
        """Streaming variant of :meth:`chat`.

        Yields event dicts as the turn progresses. Event `type` is one of:
            token        {"text": str}        — a chunk of the assistant reply
            tool_call    {"tool", "arguments"} — a tool is about to run
            tool_result  {"tool", "ok"}        — a tool finished
            done         {"tools_used": list}  — the turn is complete
            error        {"message": str}      — the turn could not start
        """
        try:
            client = get_client()
        except LLMUnavailable as exc:
            yield {"type": "error", "message": str(exc)}
            return

        convo = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        trace: list[dict] = []

        for _ in range(MAX_ITERATIONS):
            try:
                stream = client.chat.completions.create(
                    model=config.active_model(),
                    messages=convo,
                    tools=self.tool_schemas,
                    tool_choice="auto",
                    temperature=0.3,
                    stream=True,
                )
            except Exception as exc:
                logger.exception("LLM streaming request failed")
                yield {"type": "error", "message": f"LLM request failed: {exc}"}
                return

            content_parts: list[str] = []
            tool_calls: dict[int, dict] = {}

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.content:
                    content_parts.append(delta.content)
                    yield {"type": "token", "text": delta.content}

                for tc in (delta.tool_calls or []):
                    slot = tool_calls.setdefault(
                        tc.index, {"id": None, "name": "", "arguments": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["arguments"] += tc.function.arguments

            # No tool calls this turn → the streamed content was the final answer.
            if not tool_calls:
                yield {"type": "done", "tools_used": trace}
                return

            ordered = [tool_calls[i] for i in sorted(tool_calls)]
            convo.append({
                "role": "assistant",
                "content": "".join(content_parts),
                "tool_calls": [
                    {"id": s["id"], "type": "function",
                     "function": {"name": s["name"], "arguments": s["arguments"]}}
                    for s in ordered
                ],
            })

            for s in ordered:
                try:
                    args = json.loads(s["arguments"]) if s["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                yield {"type": "tool_call", "tool": s["name"], "arguments": args}
                result, entry = self._execute_tool(s["name"], s["arguments"])
                trace.append(entry)
                yield {"type": "tool_result", "tool": s["name"],
                       "ok": entry["ok"], "file": entry.get("file")}
                convo.append({
                    "role": "tool",
                    "tool_call_id": s["id"],
                    "content": json.dumps(result, default=str)[:8000],
                })

        yield {"type": "token",
               "text": "\n\n_(Reached the maximum number of tool steps.)_"}
        yield {"type": "done", "tools_used": trace}


# Module-level singleton so the registry is built once.
_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent
