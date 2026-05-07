from datetime import date
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
from chatbot_api.schemas.conversation import ConversationDetail, ConversationListItem
from chatbot_api.schemas.message import MessageRead
from chatbot_api.schemas.pagination import Page, PageParams


class ConversationService:
    def __init__(self) -> None:
        self.repository = conversation_repository
        self.messages = message_repository

    async def list_paginated(
        self,
        db: AsyncSession,
        *,
        status: ConversationStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        phone: str | None = None,
        pagination: PageParams,
    ) -> Page[ConversationListItem]:
        rows = await self.repository.list_filtered(
            db,
            status=status,
            from_date=from_date,
            to_date=to_date,
            phone=phone,
            skip=pagination.offset,
            limit=pagination.size,
        )
        total = await self.repository.count_filtered(
            db, status=status, from_date=from_date, to_date=to_date, phone=phone
        )

        items: list[ConversationListItem] = []
        for conv in rows:
            count = await self.repository.count_messages(db, conv.id)
            preview = await self.repository.last_message_preview(db, conv.id)
            items.append(
                ConversationListItem(
                    id=conv.id,
                    student_phone=conv.student_phone,
                    student_display_name=conv.student.display_name if conv.student else None,
                    status=conv.status,
                    opened_at=conv.opened_at,
                    closed_at=conv.closed_at,
                    message_count=count,
                    last_message_preview=preview,
                )
            )

        return Page(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=ceil(total / pagination.size) if total else 0,
        )

    async def get_detail(
        self, db: AsyncSession, conversation_id: int
    ) -> ConversationDetail | None:
        conv = await self.repository.get_with_messages(db, conversation_id)
        if conv is None:
            return None
        return ConversationDetail.model_validate(conv)

    async def list_messages_paginated(
        self,
        db: AsyncSession,
        conversation_id: int,
        *,
        pagination: PageParams,
    ) -> Page[MessageRead]:
        rows = await self.messages.list_by_conversation(
            db, conversation_id, skip=pagination.offset, limit=pagination.size
        )
        total = await self.messages.count_by_conversation(db, conversation_id)
        items = [MessageRead.model_validate(m) for m in rows]
        return Page(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=ceil(total / pagination.size) if total else 0,
        )


conversation_service = ConversationService()
