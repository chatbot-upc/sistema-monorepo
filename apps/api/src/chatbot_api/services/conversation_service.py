"""Business logic for conversations. Functional module (RORO), no classes."""

from datetime import date
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
from chatbot_api.schemas.conversation import ConversationDetail, ConversationListItem
from chatbot_api.schemas.message import MessageRead
from chatbot_api.schemas.pagination import Page, PageParams


async def list_paginated(
    db: AsyncSession,
    *,
    status: ConversationStatus | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    phone: str | None = None,
    pagination: PageParams,
) -> Page[ConversationListItem]:
    rows = await conversation_repository.list_filtered_with_aggregates(
        db,
        status=status,
        from_date=from_date,
        to_date=to_date,
        phone=phone,
        skip=pagination.offset,
        limit=pagination.size,
    )
    total = await conversation_repository.count_filtered(
        db, status=status, from_date=from_date, to_date=to_date, phone=phone
    )

    items = [
        ConversationListItem(
            id=conv.id,
            student_phone=conv.student_phone,
            student_display_name=conv.student.display_name if conv.student else None,
            status=conv.status,
            opened_at=conv.opened_at,
            closed_at=conv.closed_at,
            message_count=msg_count,
            last_message_preview=preview,
        )
        for conv, msg_count, preview in rows
    ]

    return Page(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )


async def get_detail(db: AsyncSession, conversation_id: int) -> ConversationDetail:
    conv = await conversation_repository.get_with_messages(db, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return ConversationDetail.model_validate(conv)


async def list_messages_paginated(
    db: AsyncSession,
    conversation_id: int,
    *,
    pagination: PageParams,
) -> Page[MessageRead]:
    rows = await message_repository.list_by_conversation(
        db, conversation_id, skip=pagination.offset, limit=pagination.size
    )
    total = await message_repository.count_by_conversation(db, conversation_id)
    items = [MessageRead.model_validate(m) for m in rows]
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )
