"""WebSocket endpoint for realtime CRM updates (SW-36/37/32).

Admins keep a single WS connection per browser tab; the server fans out
events from Redis pub/sub (see `core/events.py`) to every connected client.

Auth: browsers can't set Authorization headers on `new WebSocket(...)`, so
the client first calls POST /api/v1/auth/ws-ticket (with its real Bearer
JWT) and puts the returned opaque ticket on the WS query string. The ticket
lives 60s in Redis and is consumed (GETDEL) on first use.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from chatbot_api.core.events import EVENTS_CHANNEL
from chatbot_api.core.settings import get_settings
from chatbot_api.services import auth_service

log = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    """In-process registry of active CRM WebSocket clients."""

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


@router.websocket("/api/v1/ws/conversations")
async def conversations_stream(
    websocket: WebSocket,
    ticket: str | None = Query(None),
) -> None:
    admin_id = await auth_service.consume_ws_ticket(ticket or "")
    if admin_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(websocket)
    log.info("ws_authenticated", admin_id=admin_id)
    try:
        await websocket.send_text(
            json.dumps({"type": "hello", "data": {"admin_id": admin_id}})
        )
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
