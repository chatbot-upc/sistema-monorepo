"""Internal monitoring service (SW-28).

Aggregates message/conversation/token/queue health for a dev-facing dashboard.
SQL trips are minimized: each metric block is one query.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.celery_app import celery_app
from chatbot_api.core.settings import get_settings
from chatbot_api.core.timezone import to_local, today_local_start
from chatbot_api.models import Conversation, Message
from chatbot_api.models.enums import ConversationStatus, MessageRole
from chatbot_api.schemas.monitoring import (
    ConversationsMetrics,
    IntentClassifierMetrics,
    MessagesMetrics,
    MonitoringHealth,
    QueueMetrics,
    TokensMetrics,
)

log = structlog.get_logger()


async def get_health(db: AsyncSession) -> MonitoringHealth:
    # Ventanas móviles (última hora / 24h): comparación de instante; usa el
    # mismo reloj que el resto del código (datetime.now). "Hoy" en cambio es un
    # límite de calendario → se calcula en hora de Lima (today_local_start()).
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(hours=24)
    today_start = today_local_start()

    messages = await _messages_metrics(db, one_hour_ago, one_day_ago)
    intent = await _intent_metrics(db, one_day_ago)
    tokens = await _tokens_metrics(db, today_start)
    conversations = await _conversations_metrics(db, today_start)
    queue = await _queue_metrics()

    return MonitoringHealth(
        messages=messages,
        intent_classifier=intent,
        tokens=tokens,
        conversations=conversations,
        queue=queue,
    )


async def _messages_metrics(
    db: AsyncSession, one_hour_ago: datetime, one_day_ago: datetime
) -> MessagesMetrics:
    last_hour_subq = func.count(
        case((Message.created_at >= one_hour_ago, Message.id))
    )
    last_24h_subq = func.count(Message.id)
    bot_latency_avg = func.avg(
        case((Message.role == MessageRole.bot, Message.latency_ms))
    )
    bot_latency_p95 = func.percentile_cont(0.95).within_group(
        case((Message.role == MessageRole.bot, Message.latency_ms))
    )

    row = (
        await db.execute(
            select(
                last_hour_subq,
                last_24h_subq,
                bot_latency_avg,
                bot_latency_p95,
            ).where(Message.created_at >= one_day_ago)
        )
    ).one()

    return MessagesMetrics(
        last_hour=int(row[0] or 0),
        last_24h=int(row[1] or 0),
        avg_latency_ms=float(row[2]) if row[2] is not None else None,
        p95_latency_ms=float(row[3]) if row[3] is not None else None,
    )


async def _intent_metrics(
    db: AsyncSession, one_day_ago: datetime
) -> IntentClassifierMetrics:
    total = func.count(Message.id)
    fallback = func.count(case((Message.intent_used_fallback.is_(True), Message.id)))
    row = (
        await db.execute(
            select(total, fallback).where(
                Message.created_at >= one_day_ago,
                Message.role == MessageRole.student,
                Message.intent_used_fallback.isnot(None),
            )
        )
    ).one()
    classified = int(row[0] or 0)
    fb = int(row[1] or 0)
    if classified == 0:
        return IntentClassifierMetrics(
            classified_last_24h=0,
            sbert_only_pct=None,
            fallback_to_llm_pct=None,
        )
    fallback_pct = round(100 * fb / classified, 1)
    return IntentClassifierMetrics(
        classified_last_24h=classified,
        sbert_only_pct=round(100 - fallback_pct, 1),
        fallback_to_llm_pct=fallback_pct,
    )


async def _tokens_metrics(
    db: AsyncSession, today_start: datetime
) -> TokensMetrics:
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(Message.input_tokens), 0),
                func.coalesce(func.sum(Message.output_tokens), 0),
            ).where(to_local(Message.created_at) >= today_start)
        )
    ).one()
    return TokensMetrics(input_today=int(row[0]), output_today=int(row[1]))


async def _conversations_metrics(
    db: AsyncSession, today_start: datetime
) -> ConversationsMetrics:
    open_count = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.status == ConversationStatus.abierta
            )
        )
    ).scalar_one()
    takeover_count = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.status == ConversationStatus.takeover
            )
        )
    ).scalar_one()
    closed_today = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.status == ConversationStatus.cerrada,
                to_local(Conversation.closed_at) >= today_start,
            )
        )
    ).scalar_one()
    return ConversationsMetrics(
        open=int(open_count),
        takeover=int(takeover_count),
        closed_today=int(closed_today),
    )


async def _queue_metrics() -> QueueMetrics:
    pending = await _redis_queue_length()
    workers = await asyncio.to_thread(_celery_workers_alive)
    return QueueMetrics(pending=pending, workers_alive=workers)


async def _redis_queue_length() -> int:
    settings = get_settings()
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.celery_broker_url)
        try:
            return int(await client.llen("celery"))
        finally:
            await client.aclose()
    except Exception:
        log.exception("monitoring_redis_queue_failed")
        return -1


def _celery_workers_alive() -> int:
    try:
        ping: dict[str, Any] | None = celery_app.control.inspect(timeout=1).ping()
        return len(ping or {})
    except Exception:
        log.exception("monitoring_celery_inspect_failed")
        return -1
