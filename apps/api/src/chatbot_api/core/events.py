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
from typing import TYPE_CHECKING, Any

import structlog

from chatbot_api.core.settings import get_settings

if TYPE_CHECKING:
    from chatbot_api.models import Message

log = structlog.get_logger()

EVENTS_CHANNEL = "chatbot:events"


def message_to_event_payload(msg: Message) -> dict[str, Any]:
    """Flat shape the CRM consumes via WebSocket. Matches schemas.MessageRead
    closely so the client can reuse the same renderer for fetch + stream paths.
    Shared between the Celery worker (inbound/bot replies) and the
    conversation_service (admin replies, takeover, close, reopen).
    """
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "role": msg.role.value,
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "meta_message_id": msg.meta_message_id,
        "intent_id": msg.intent_id,
        "latency_ms": msg.latency_ms,
        "admin_id": msg.admin_id,
        "in_reply_to_id": msg.in_reply_to_id,
        "quoted": msg.quoted,
        "delivery_status": msg.delivery_status,
    }


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
