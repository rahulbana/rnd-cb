"""Pure-ASGI observability middleware.

Implemented at the ASGI level (rather than Starlette's BaseHTTPMiddleware) so it
never buffers the response body — important for the streaming SSE endpoint.
Records request count, latency, and in-progress gauge, and emits an access log
line per request.
"""
from __future__ import annotations

import time

from ..core.logging import get_logger
from .metrics import HTTP_IN_PROGRESS, HTTP_LATENCY, HTTP_REQUESTS

logger = get_logger("app.access")


class ObservabilityMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        HTTP_IN_PROGRESS.labels(method=method, path=path).inc()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            HTTP_IN_PROGRESS.labels(method=method, path=path).dec()
            HTTP_LATENCY.labels(method=method, path=path).observe(duration)
            HTTP_REQUESTS.labels(
                method=method, path=path, status=str(status_code)
            ).inc()
            logger.info(
                "%s %s -> %s (%.1f ms)", method, path, status_code, duration * 1000
            )
