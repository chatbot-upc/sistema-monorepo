"""Business logic for reports. Functional module (RORO), no classes."""

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import (
    Conversation,
    ConversationIntent,
    Document,
    Intent,
    Message,
)
from chatbot_api.models.enums import ConversationStatus, DocumentStatus


async def get_dashboard_stats(db: AsyncSession) -> dict[str, int]:
    today_start = datetime.combine(date.today(), time.min)

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
    conversations_today = (
        await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.opened_at >= today_start
            )
        )
    ).scalar_one()
    messages_today = (
        await db.execute(
            select(func.count(Message.id)).where(Message.created_at >= today_start)
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

    return {
        "conversations_total": int(conversations_total),
        "conversations_open": int(conversations_open),
        "conversations_today": int(conversations_today),
        "messages_today": int(messages_today),
        "documents_indexed": int(documents_indexed),
        "intents_active": int(intents_active),
    }


async def get_conversations_by_day(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> list[dict[str, Any]]:
    from_dt = datetime.combine(from_date, time.min)
    to_dt = datetime.combine(to_date, time.max)
    day_col = cast(Conversation.opened_at, Date).label("day")
    result = await db.execute(
        select(day_col, func.count(Conversation.id).label("conv_count"))
        .where(Conversation.opened_at >= from_dt, Conversation.opened_at <= to_dt)
        .group_by(day_col)
        .order_by(day_col)
    )
    return [{"date": row.day.isoformat(), "count": int(row.conv_count)} for row in result]


async def get_intent_distribution(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> list[dict[str, Any]]:
    from_dt = datetime.combine(from_date, time.min)
    to_dt = datetime.combine(to_date, time.max)
    result = await db.execute(
        select(
            Intent.name.label("intent_name"),
            func.count(ConversationIntent.intent_id).label("intent_count"),
        )
        .join(Intent, Intent.id == ConversationIntent.intent_id)
        .where(
            ConversationIntent.detected_at >= from_dt,
            ConversationIntent.detected_at <= to_dt,
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
