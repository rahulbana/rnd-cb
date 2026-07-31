"""ASGI middleware that records each API request as one Langfuse trace.

The whole interaction lands in a single trace: the request payload as the
trace input, the response payload as the output, attributed to the user and
working session — with the endpoint's own LLM/tool spans nested underneath.
No-op unless request tracing is enabled and Langfuse is configured.
"""
from __future__ import annotations

import json

from app.core.config import settings
from app.core.security import decode_access_token
from app.services import observability as obs

# Only capture JSON bodies, and cap sizes so large payloads/uploads (e.g.
# multipart file uploads, PDF/DOCX exports) are never buffered.
_MAX_REQ_BYTES = 64 * 1024
_MAX_RESP_BYTES = 128 * 1024
_SENSITIVE_KEYS = {"password", "hashed_password", "access_token", "token", "secret"}


def _redact(obj):
    if isinstance(obj, dict):
        return {
            k: ("***" if k.lower() in _SENSITIVE_KEYS else _redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, str) and len(obj) > 2000:
        return obj[:2000] + "…"
    return obj


def _parse_json(raw: bytes):
    if not raw:
        return None
    try:
        return _redact(json.loads(raw))
    except Exception:
        text = raw.decode("utf-8", errors="ignore")
        return text[:2000] + ("…" if len(text) > 2000 else "")


class LangfuseTracingMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or not settings.LANGFUSE_TRACE_REQUESTS
            or not obs.is_enabled()
        ):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        if method == "OPTIONS" or not path.startswith(settings.API_V1_PREFIX):
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}

        # --- buffer a small JSON request body (leave uploads untouched) ---
        content_type = headers.get("content-type", "")
        content_length = int(headers.get("content-length") or 0)
        capture_req = (
            method in ("POST", "PUT", "PATCH")
            and "application/json" in content_type
            and 0 < content_length <= _MAX_REQ_BYTES
        )
        receive_to_use = receive
        req_body = b""
        if capture_req:
            buffered: list[dict] = []
            while True:
                message = await receive()
                buffered.append(message)
                if message["type"] == "http.request":
                    req_body += message.get("body", b"")
                    if not message.get("more_body"):
                        break
                else:
                    break

            async def replay_receive():
                if buffered:
                    return buffered.pop(0)
                return await receive()

            receive_to_use = replay_receive

        # --- capture response status + small JSON body ---
        state = {"status": None, "capture": False, "body": bytearray()}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                state["status"] = message["status"]
                rheaders = {
                    k.decode().lower(): v.decode()
                    for k, v in message.get("headers", [])
                }
                state["capture"] = "application/json" in rheaders.get("content-type", "")
            elif message["type"] == "http.response.body" and state["capture"]:
                if len(state["body"]) < _MAX_RESP_BYTES:
                    state["body"].extend(message.get("body", b""))
            await send(message)

        user_id = decode_access_token(headers["authorization"].split(" ", 1)[1]) if (
            "authorization" in headers and headers["authorization"].lower().startswith("bearer ")
        ) else None
        session_id = headers.get("x-session-id")

        with obs.span(f"{method} {path}", input={"method": method, "path": path}):
            obs.set_trace(
                name=f"{method} {path}",
                user_id=user_id,
                session_id=session_id,
                input={
                    "method": method,
                    "path": path,
                    "query": scope.get("query_string", b"").decode(),
                    "body": _parse_json(req_body) if capture_req else None,
                },
            )
            try:
                await self.app(scope, receive_to_use, send_wrapper)
            finally:
                obs.set_trace(
                    output={
                        "status": state["status"],
                        "body": _parse_json(bytes(state["body"]))
                        if state["capture"]
                        else None,
                    }
                )
