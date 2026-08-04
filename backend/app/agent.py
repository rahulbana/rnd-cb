"""OpenAI tool-use agent loop."""
from __future__ import annotations

import json
import uuid
from typing import Awaitable, Callable

from openai import AsyncOpenAI

from . import repository as repo
from . import tools
from .config import openai_api_key, settings
from .schemas import ApprovalRequest, ChatMessage, ToolCallRecord

MAX_STEPS = 20

SYSTEM_PROMPT = """You are an AI coding agent embedded in a desktop application.
You help the user build and modify software in their local project directory.

You have tools to list files, read files, write files, and run shell commands.
Guidelines:
- Explore the project with list_files and read_file before making changes.
- Make focused, correct edits. When writing a file, provide its complete new content.
- Prefer running tests or builds with run_command to verify your work.
- Explain what you did and why in clear, concise prose.
- Never touch files outside the project directory."""

SIDE_EFFECTING_TOOLS = {"write_file", "run_command"}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files and directories within the project. Returns paths relative to the "
                "project root. Common build/vendor dirs are skipped."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dir": {
                        "type": "string",
                        "description": "Subdirectory to list, relative to project root. Defaults to the whole project.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file within the project.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path relative to the project root."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or overwrite a text file within the project with the given full content. "
                "Parent directories are created as needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to the project root."},
                    "content": {"type": "string", "description": "The complete new content of the file."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command from the project root and return its combined stdout/stderr and "
                "exit code. Use for building, testing, git, installing dependencies, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "The shell command to execute."}},
                "required": ["command"],
            },
        },
    },
]

# Callback types.
Emit = Callable[[dict], Awaitable[None]]
RequestApproval = Callable[[ApprovalRequest], Awaitable[bool]]
IsCancelled = Callable[[], bool]


def _summarize_tool_call(name: str, args: dict) -> tuple[str, str]:
    if name == "write_file":
        return f"Write file: {args.get('path')}", str(args.get("content", ""))[:2000]
    if name == "run_command":
        return f"Run command: {args.get('command')}", str(args.get("command", ""))
    return name, json.dumps(args)


async def _execute_tool(root: str, name: str, args: dict) -> str:
    if name == "list_files":
        return tools.list_files(root, args.get("dir", "."))
    if name == "read_file":
        return tools.read_file(root, str(args["path"]))
    if name == "write_file":
        return tools.write_file(root, str(args["path"]), str(args.get("content", "")))
    if name == "run_command":
        return await tools.run_command(root, str(args["command"]))
    raise ValueError(f"Unknown tool: {name}")


class AgentRunner:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Construct the OpenAI client lazily so the backend can start (and
        report "no API key") even when OPENAI_API_KEY is unset."""
        key = openai_api_key()
        if not key:
            raise RuntimeError(
                "OpenAI API key not configured. Set OPENAI_API_KEY in backend/.env and restart the backend."
            )
        if self._client is None:
            self._client = AsyncOpenAI(api_key=key)
        return self._client

    async def run(
        self,
        conversation_id: str,
        emit: Emit,
        request_approval: RequestApproval,
        is_cancelled: IsCancelled,
    ) -> None:
        root = settings.project_path or "."
        model = settings.model
        try:
            client = self._get_client()
            history = await repo.get_messages(conversation_id)
            messages = self._to_openai_messages(history)

            for _ in range(MAX_STEPS):
                if is_cancelled():
                    break

                completion = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                )
                choice = completion.choices[0].message
                tool_calls = choice.tool_calls or []
                records = [
                    ToolCallRecord(id=tc.id, name=tc.function.name, arguments=tc.function.arguments)
                    for tc in tool_calls
                ]

                if choice.content:
                    await emit({"type": "assistant_text", "conversationId": conversation_id, "content": choice.content})

                await repo.add_message(
                    conversation_id,
                    "assistant",
                    choice.content or "",
                    tool_calls=records or None,
                )

                messages.append(
                    {
                        "role": "assistant",
                        "content": choice.content or "",
                        **(
                            {
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": "function",
                                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                                    }
                                    for tc in tool_calls
                                ]
                            }
                            if tool_calls
                            else {}
                        ),
                    }
                )

                if not tool_calls:
                    break

                for call in records:
                    if is_cancelled():
                        break
                    await emit({"type": "tool_call", "conversationId": conversation_id, "call": call.model_dump()})
                    result = await self._execute_with_approval(root, call, request_approval)

                    await repo.add_message(
                        conversation_id, "tool", result, tool_call_id=call.id, name=call.name
                    )
                    await emit(
                        {
                            "type": "tool_result",
                            "conversationId": conversation_id,
                            "toolCallId": call.id,
                            "name": call.name,
                            "content": result,
                        }
                    )
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

            await self._maybe_auto_title(conversation_id, history, model)
            await repo.touch_conversation(conversation_id)
            await emit({"type": "done", "conversationId": conversation_id})
        except Exception as exc:  # noqa: BLE001
            await emit({"type": "error", "conversationId": conversation_id, "message": str(exc)})
            await emit({"type": "done", "conversationId": conversation_id})

    async def _execute_with_approval(
        self, root: str, call: ToolCallRecord, request_approval: RequestApproval
    ) -> str:
        try:
            args = json.loads(call.arguments) if call.arguments else {}
        except json.JSONDecodeError:
            return f"Error: could not parse arguments for {call.name}: {call.arguments}"

        if call.name in SIDE_EFFECTING_TOOLS and settings.permission_mode == "ask":
            summary, details = _summarize_tool_call(call.name, args)
            approved = await request_approval(
                ApprovalRequest(id=str(uuid.uuid4()), tool=call.name, summary=summary, details=details)
            )
            if not approved:
                return f"The user declined to run this {call.name} operation."

        try:
            return await _execute_tool(root, call.name, args)
        except Exception as exc:  # noqa: BLE001
            return f"Error running {call.name}: {exc}"

    @staticmethod
    def _to_openai_messages(history: list[ChatMessage]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history:
            if m.role == "user":
                out.append({"role": "user", "content": m.content})
            elif m.role == "assistant":
                msg: dict = {"role": "assistant", "content": m.content}
                if m.toolCalls:
                    msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": tc.arguments},
                        }
                        for tc in m.toolCalls
                    ]
                out.append(msg)
            elif m.role == "tool" and m.toolCallId:
                out.append({"role": "tool", "tool_call_id": m.toolCallId, "content": m.content})
        return out

    async def _maybe_auto_title(self, conversation_id: str, prior_history: list[ChatMessage], model: str) -> None:
        prior_user_turns = sum(1 for m in prior_history if m.role == "user")
        if prior_user_turns != 1:
            return
        first_user = next((m for m in prior_history if m.role == "user"), None)
        if not first_user:
            return
        try:
            res = await self._get_client().chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Generate a short (max 6 words) title for this coding task. Reply with the title only, no quotes.",
                    },
                    {"role": "user", "content": first_user.content[:500]},
                ],
                max_tokens=20,
            )
            title = (res.choices[0].message.content or "").strip().strip("\"'")
            if title:
                await repo.rename_conversation(conversation_id, title[:80])
        except Exception:  # noqa: BLE001
            pass
