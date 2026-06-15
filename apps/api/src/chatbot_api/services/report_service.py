"""Business logic for reports. Functional module (RORO), no classes."""

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.timezone import to_local as _local
from chatbot_api.core.timezone import today_local_start
from chatbot_api.models import (
    Conversation,
    ConversationIntent,
    Document,
    Intent,
    Message,
)
from chatbot_api.models.enums import (
    ConversationStatus,
    DocumentStatus,
    MessageRole,
)


async def get_dashboard_stats(db: AsyncSession) -> dict[str, Any]:
    """KPIs del día para el panel de inicio (SW-40 / HU31).

    Devuelve los 4 KPIs de la HU (activas, escaladas, tema top, certeza) más
    métricas de soporte (latencia, conteos del día) que el dashboard consume.
    """
    today_start = today_local_start()

    conversations_total = (
        await db.execute(select(func.count(Conversation.id)))
    ).scalar_one()
    conversations_open = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.status == ConversationStatus.abierta
            )
        )
    ).scalar_one()
    conversations_escalated = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.status == ConversationStatus.takeover
            )
        )
    ).scalar_one()
    conversations_today = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                _local(Conversation.opened_at) >= today_start
            )
        )
    ).scalar_one()
    messages_today = (
        await db.execute(
            select(func.count(Message.id)).where(
                _local(Message.created_at) >= today_start
            )
        )
    ).scalar_one()
    documents_indexed = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.status == DocumentStatus.indexed
            )
        )
    ).scalar_one()
    intents_active = (
        await db.execute(select(func.count(Intent.id)).where(Intent.active.is_(True)))
    ).scalar_one()

    # Tema top del día: intención más frecuente detectada hoy.
    top_intent_row = (
        await db.execute(
            select(
                Intent.name.label("intent_name"),
                func.count(ConversationIntent.intent_id).label("intent_count"),
            )
            .join(Intent, Intent.id == ConversationIntent.intent_id)
            .where(_local(ConversationIntent.detected_at) >= today_start)
            .group_by(Intent.name)
            .order_by(func.count(ConversationIntent.intent_id).desc())
            .limit(1)
        )
    ).first()
    top_intent = (
        {"name": top_intent_row.intent_name, "count": int(top_intent_row.intent_count)}
        if top_intent_row
        else None
    )

    # Certeza: confianza promedio de las intenciones detectadas hoy.
    avg_confidence = (
        await db.execute(
            select(func.avg(ConversationIntent.confidence)).where(
                _local(ConversationIntent.detected_at) >= today_start
            )
        )
    ).scalar()

    # Latencia promedio de las respuestas del bot hoy.
    avg_latency = (
        await db.execute(
            select(func.avg(Message.latency_ms)).where(
                _local(Message.created_at) >= today_start,
                Message.latency_ms.is_not(None),
            )
        )
    ).scalar()

    return {
        "conversations_total": int(conversations_total),
        "conversations_open": int(conversations_open),
        "conversations_active": int(conversations_open),
        "conversations_escalated": int(conversations_escalated),
        "conversations_today": int(conversations_today),
        "messages_today": int(messages_today),
        "documents_indexed": int(documents_indexed),
        "intents_active": int(intents_active),
        "top_intent": top_intent,
        "avg_confidence": round(float(avg_confidence), 4) if avg_confidence else 0.0,
        "avg_latency_ms": int(avg_latency) if avg_latency else None,
    }


async def get_conversations_by_day(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> list[dict[str, Any]]:
    from_dt = datetime.combine(from_date, time.min)
    to_dt = datetime.combine(to_date, time.max)
    conv_local = _local(Conversation.opened_at)
    day_col = cast(conv_local, Date).label("day")
    result = await db.execute(
        select(day_col, func.count(Conversation.id).label("conv_count"))
        .where(conv_local >= from_dt, conv_local <= to_dt)
        .group_by(day_col)
        .order_by(day_col)
    )
    return [{"date": row.day.isoformat(), "count": int(row.conv_count)} for row in result]


async def _summary_counts(
    db: AsyncSession, from_dt: datetime, to_dt: datetime
) -> tuple[int, int, int, int]:
    """(total convs, escaladas, mensajes bot, mensajes bot con fallback) en rango."""
    conv_local = _local(Conversation.opened_at)
    msg_local = _local(Message.created_at)
    total = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                conv_local >= from_dt, conv_local <= to_dt
            )
        )
    ).scalar_one()
    escalated = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                conv_local >= from_dt,
                conv_local <= to_dt,
                Conversation.status == ConversationStatus.takeover,
            )
        )
    ).scalar_one()
    bot_msgs = (
        await db.execute(
            select(func.count(Message.id)).where(
                msg_local >= from_dt,
                msg_local <= to_dt,
                Message.role == MessageRole.bot,
            )
        )
    ).scalar_one()
    fallback_msgs = (
        await db.execute(
            select(func.count(Message.id)).where(
                msg_local >= from_dt,
                msg_local <= to_dt,
                Message.role == MessageRole.bot,
                Message.intent_used_fallback.is_(True),
            )
        )
    ).scalar_one()
    return int(total), int(escalated), int(bot_msgs), int(fallback_msgs)


async def get_report_summary(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    """KPIs del rango + comparación contra el periodo inmediatamente anterior."""
    from_dt = datetime.combine(from_date, time.min)
    to_dt = datetime.combine(to_date, time.max)

    period_days = (to_date - from_date).days + 1
    prev_to_date = from_date - timedelta(days=1)
    prev_from_date = prev_to_date - timedelta(days=period_days - 1)
    prev_from_dt = datetime.combine(prev_from_date, time.min)
    prev_to_dt = datetime.combine(prev_to_date, time.max)

    total, escalated, bot_msgs, fallback_msgs = await _summary_counts(
        db, from_dt, to_dt
    )
    p_total, _p_esc, p_bot, p_fallback = await _summary_counts(
        db, prev_from_dt, prev_to_dt
    )

    resolved = total - escalated
    fallback_rate = round(fallback_msgs * 100 / bot_msgs, 1) if bot_msgs else 0.0
    prev_fallback_rate = round(p_fallback * 100 / p_bot, 1) if p_bot else 0.0

    return {
        "total": total,
        "total_change_pct": (
            round((total - p_total) * 100 / p_total, 1) if p_total else None
        ),
        "resolved_by_bot": resolved,
        "resolved_pct_of_total": round(resolved * 100 / total, 1) if total else 0.0,
        "escalated": escalated,
        "escalated_pct_of_total": (
            round(escalated * 100 / total, 1) if total else 0.0
        ),
        "fallback_rate": fallback_rate,
        "fallback_change_pp": (
            round(fallback_rate - prev_fallback_rate, 1) if p_bot else None
        ),
    }


async def get_intent_distribution(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> list[dict[str, Any]]:
    from_dt = datetime.combine(from_date, time.min)
    to_dt = datetime.combine(to_date, time.max)
    detected_local = _local(ConversationIntent.detected_at)
    result = await db.execute(
        select(
            Intent.name.label("intent_name"),
            func.count(ConversationIntent.intent_id).label("intent_count"),
        )
        .join(Intent, Intent.id == ConversationIntent.intent_id)
        .where(
            detected_local >= from_dt,
            detected_local <= to_dt,
        )
        .group_by(Intent.name)
        .order_by(func.count(ConversationIntent.intent_id).desc())
    )
    rows = list(result)
    total = sum(int(r.intent_count) for r in rows) or 1
    return [
        {
            "intent_name": r.intent_name,
            "count": int(r.intent_count),
            "percentage": round(int(r.intent_count) * 100 / total, 2),
        }
        for r in rows
    ]
