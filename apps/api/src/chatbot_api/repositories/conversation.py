from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from chatbot_api.models import Conversation, Message, Student
from chatbot_api.models.enums import ConversationStatus

from .base import BaseRepository


class _ConvCreate(BaseModel):
    pass


class _ConvUpdate(BaseModel):
    pass


def _truncate(content: str | None, length: int = 80) -> str | None:
    if content is None:
        return None
    return content if len(content) <= length else content[: length - 3] + "..."


class ConversationRepository(BaseRepository[Conversation, _ConvCreate, _ConvUpdate]):
    def _apply_filters(
        self,
        query: Select[Any],
        *,
        status: ConversationStatus | None,
        from_date: date | None,
        to_date: date | None,
        phone: str | None,
    ) -> Select[Any]:
        if status is not None:
            query = query.where(Conversation.status == status)
        if from_date is not None:
            query = query.where(Conversation.opened_at >= datetime.combine(from_date, time.min))
        if to_date is not None:
            query = query.where(Conversation.opened_at <= datetime.combine(to_date, time.max))
        if phone:
            query = query.join(Student, Conversation.student_phone == Student.phone_e164)
            query = query.where(Student.display_name.op("%")(phone))
        return query

    async def list_filtered_with_aggregates(
        self,
        db: AsyncSession,
        *,
        status: ConversationStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        phone: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[tuple[Conversation, int, str | None]]:
        """Single query: (Conversation, message_count, last_message_preview)."""
        msg_count_subq = (
            select(func.count(Message.id))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        last_msg_subq = (
            select(Message.content)
            .where(Message.conversation_id == Conversation.id)
            .order_by(Message.created_at.desc())
            .limit(1)
            .correlate(Conversation)
            .scalar_subquery()
        )

        query = select(
            Conversation,
            msg_count_subq.label("message_count"),
            last_msg_subq.label("last_message_content"),
        ).options(selectinload(Conversation.student))
        query = self._apply_filters(
            query, status=status, from_date=from_date, to_date=to_date, phone=phone
        )
        query = query.order_by(Conversation.opened_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        rows = result.unique().all()
        return [
            (row[0], int(row.message_count), _truncate(row.last_message_content))
            for row in rows
        ]

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        status: ConversationStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        phone: str | None = None,
    ) -> int:
        query: Select[tuple[Conversation]] = select(Conversation)
        query = self._apply_filters(
            query, status=status, from_date=from_date, to_date=to_date, phone=phone
        )
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        return int(result.scalar_one())

    async def get_with_messages(
        self, db: AsyncSession, conversation_id: int
    ) -> Conversation | None:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages), selectinload(Conversation.student))
            .where(Conversation.id == conversation_id)
        )
        return result.scalars().first()

    async def get_or_create_open(
        self, db: AsyncSession, student_phone: str
    ) -> tuple[Conversation, bool]:
        """Return latest open/takeover conversation for phone or create a fresh one.

        Returns (conversation, created) where `created` is True only on first contact.
        """
        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.student_phone == student_phone,
                Conversation.status.in_(
                    [ConversationStatus.abierta, ConversationStatus.takeover]
                ),
            )
            .order_by(Conversation.opened_at.desc())
            .limit(1)
        )
        existing = result.scalars().first()
        if existing is not None:
            return existing, False
        conv = Conversation(
            student_phone=student_phone, status=ConversationStatus.abierta
        )
        db.add(conv)
        await db.flush()
        return conv, True


conversation_repository = ConversationRepository(Conversation)
