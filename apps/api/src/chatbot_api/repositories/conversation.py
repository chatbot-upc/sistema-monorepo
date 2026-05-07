from datetime import date, datetime, time

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


class ConversationRepository(BaseRepository[Conversation, _ConvCreate, _ConvUpdate]):
    def _apply_filters(
        self,
        query: Select[tuple[Conversation]],
        *,
        status: ConversationStatus | None,
        from_date: date | None,
        to_date: date | None,
        phone: str | None,
    ) -> Select[tuple[Conversation]]:
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

    async def list_filtered(
        self,
        db: AsyncSession,
        *,
        status: ConversationStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        phone: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Conversation]:
        query = select(Conversation).options(selectinload(Conversation.student))
        query = self._apply_filters(
            query, status=status, from_date=from_date, to_date=to_date, phone=phone
        )
        query = query.order_by(Conversation.opened_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().unique().all())

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

    async def count_messages(self, db: AsyncSession, conversation_id: int) -> int:
        result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        )
        return int(result.scalar_one())

    async def last_message_preview(
        self, db: AsyncSession, conversation_id: int
    ) -> str | None:
        result = await db.execute(
            select(Message.content)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        content = result.scalar_one_or_none()
        if content is None:
            return None
        return content if len(content) <= 80 else content[:77] + "..."

    async def get_with_messages(
        self, db: AsyncSession, conversation_id: int
    ) -> Conversation | None:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages), selectinload(Conversation.student))
            .where(Conversation.id == conversation_id)
        )
        return result.scalars().first()


conversation_repository = ConversationRepository(Conversation)
