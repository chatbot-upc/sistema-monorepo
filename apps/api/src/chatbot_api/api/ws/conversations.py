"""WebSocket endpoint for realtime CRM updates (SW-36/37/32).

Admins keep a single WS connection per browser tab; the server fans out
events from Redis pub/sub (see `core/events.py`) to every connected client.

Auth: a real Auth.js bearer doesn't come through automatically on the
WebSocket handshake (browsers don't let you set Authorization headers on
`new WebSocket()`), so we accept the admin email via cookie/query param.
In env=local this is the dev-bypass header equivalent; production should
use a short-lived JWT in the query param.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from chatbot_api.core.events import EVENTS_CHANNEL
from chatbot_api.core.settings import get_settings

log = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    """In-process registry of active CRM WebSocket clients.

    For the pilot we run a single API instance, so an in-memory set is fine.
    If we scale out, every instance keeps its own set and Redis pub/sub still
    delivers to all of them — same code path.
    """

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        log.info("ws_client_connected", total=len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        log.info("ws_client_disconnected", total=len(self._clients))

    async def broadcast(self, payload: str) -> None:
        # Snapshot then iterate without holding the lock so a slow client can't
        # stall every other broadcast.
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)


manager = ConnectionManager()


async def _redis_subscriber_loop() -> None:
    """Background task: forward every Redis event into connected WS clients."""
    settings = get_settings()
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url)
        try:
            pubsub = client.pubsub()
            await pubsub.subscribe(EVENTS_CHANNEL)
            log.info("ws_subscriber_started", channel=EVENTS_CHANNEL)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                if not isinstance(data, str):
                    continue
                await manager.broadcast(data)
        finally:
            await client.aclose()
    except asyncio.CancelledError:
        log.info("ws_subscriber_cancelled")
        raise
    except Exception:
        log.exception("ws_subscriber_failed")


def _authorize(websocket: WebSocket) -> bool:
    """In env=local we trust any connection (dev workflow with admin in CRM).
    In staging/production we will gate by a real JWT verified in Cognito,
    read from the cookie that travels with the WS handshake. Fail closed."""
    settings = get_settings()
    if settings.env == "local":
        return True
    # Placeholder until we wire Auth.js JWT verification:
    cookie_header = next(
        (v for k, v in (websocket.scope.get("headers") or []) if k == b"cookie"),
        None,
    )
    return cookie_header is not None  # presence-only stub


@router.websocket("/api/v1/ws/conversations")
async def conversations_stream(websocket: WebSocket) -> None:
    if not _authorize(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(websocket)
    try:
        # Send a hello frame so the client can log/connect happily even when
        # no events are pending.
        await websocket.send_text(json.dumps({"type": "hello", "data": {}}))
        # The CRM doesn't push anything back; we just keep the connection alive
        # and react to client disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws_handler_error")
    finally:
        await manager.disconnect(websocket)


def _broadcast_sync(payload: dict[str, Any]) -> None:
    """Test helper bypassing Redis."""
    asyncio.run(manager.broadcast(json.dumps(payload)))
