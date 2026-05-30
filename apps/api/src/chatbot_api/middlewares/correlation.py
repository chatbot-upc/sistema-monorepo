"""Correlation-ID middleware (ASGI raw, not BaseHTTPMiddleware).

BaseHTTPMiddleware does NOT support WebSocket scopes — Starlette rejects WS
requests with 400 Bad Request before our handler runs. We use the raw ASGI
interface so the middleware passes WebSocket connections through cleanly.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import structlog

CORRELATION_ID_HEADER = "X-Correlation-Id"
_HEADER_BYTES = CORRELATION_ID_HEADER.lower().encode()


class CorrelationMiddleware:
    """Reads/generates a correlation_id, binds it to structlog contextvars,
    and echoes it back on HTTP responses. WebSocket scopes get the same
    binding so any log inside the handler still carries the id."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        cid_bytes = headers.get(_HEADER_BYTES)
        correlation_id = cid_bytes.decode() if cid_bytes else uuid4().hex

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        if scope["type"] == "websocket":
            await self.app(scope, receive, send)
            return

        async def _send(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                response_headers = list(message.get("headers") or [])
                response_headers.append(
                    (_HEADER_BYTES, correlation_id.encode())
                )
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, receive, _send)
