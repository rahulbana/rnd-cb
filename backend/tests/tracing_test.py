"""Verify the request-tracing middleware captures I/O and redacts secrets."""
import asyncio
import os
import tempfile
from contextlib import contextmanager

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["DEBUG"] = "false"
os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["WEB_SEARCH_PROVIDER"] = "none"

import httpx  # noqa: E402

from app.core.tracing import _parse_json, _redact  # noqa: E402
from app.services import observability as obs  # noqa: E402


def unit_checks() -> None:
    assert _redact({"email": "a@b.com", "password": "hunter2"})["password"] == "***"
    assert _redact({"nested": {"access_token": "x"}})["nested"]["access_token"] == "***"
    assert _parse_json(b'{"a": 1}') == {"a": 1}
    assert _parse_json(b"") is None
    print("unit: redaction + json parsing OK")


async def middleware_checks() -> None:
    # Stub the tracer: enabled, no-op spans, record set_trace calls.
    calls: list[dict] = []
    obs.is_enabled = lambda: True  # type: ignore

    @contextmanager
    def fake_span(name, **kw):
        yield object()

    obs.span = fake_span  # type: ignore
    obs.set_trace = lambda **kw: calls.append(kw)  # type: ignore

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/auth/register",
                json={"email": "trace@example.com", "password": "supersecret1"},
            )
            assert r.status_code == 201, r.text

    # There should be an input call (with redacted body) and an output call.
    inputs = [c for c in calls if "input" in c]
    outputs = [c for c in calls if "output" in c]
    assert inputs, "no trace input recorded"
    assert outputs, "no trace output recorded"

    body = inputs[0]["input"]["body"]
    assert body["email"] == "trace@example.com"
    assert body["password"] == "***", f"password not redacted: {body}"
    assert inputs[0]["input"]["path"] == "/api/v1/auth/register"

    out = outputs[-1]["output"]
    assert out["status"] == 201, out
    # register returns a token; response body should be captured (redacted)
    assert out["body"]["access_token"] == "***", out
    print("middleware: request/response captured, secrets redacted OK")


if __name__ == "__main__":
    unit_checks()
    asyncio.run(middleware_checks())
    print("\nTRACING MIDDLEWARE TEST PASSED ✅")
