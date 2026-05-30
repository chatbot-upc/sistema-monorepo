"""Cross-process event bus on Redis pub/sub.

Worker (Celery) publishes events when it persists/sends a message; the API
process subscribes to the channel and broadcasts to connected WebSocket
clients (CRM admins). Redis is already in the stack — no extra infra.

Event payload shape:
    {
        "type": "message.created" | "conversation.escalated" | "conversation.status_changed",
        "data": { ... },
        "ts": "2026-05-29T18:43:17Z",
    }

Failures publishing are logged but never raised — a missed realtime update
must not break the conversation pipeline.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog

from chatbot_api.core.settings import get_settings

log = structlog.get_logger()

EVENTS_CHANNEL = "chatbot:events"


async def publish_event(event_type: str, data: dict[str, Any]) -> None:
    """Best-effort publish to the events channel.

    Builds a fresh Redis client per call: workers spin a new asyncio loop per
    Celery task, so a process-wide client would tie its connection pool to a
    dead loop on the second task (same lesson as whatsapp_service).
    """
    settings = get_settings()
    payload = {
        "type": event_type,
        "data": data,
        "ts": datetime.now(UTC).isoformat(),
    }
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url)
        try:
            await client.publish(EVENTS_CHANNEL, json.dumps(payload))
        finally:
            await client.aclose()
    except Exception:
        log.exception("event_publish_failed", event_type=event_type)
