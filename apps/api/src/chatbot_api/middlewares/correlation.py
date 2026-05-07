from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-Id"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Adds a correlation_id to every request: read from header or generate new one.

    Binds it to structlog contextvars so any log inside the request handler
    automatically carries it. Returns it in the response headers.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or uuid4().hex

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
