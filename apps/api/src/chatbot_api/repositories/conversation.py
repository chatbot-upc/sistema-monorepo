from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from chatbot_api.core.timezone import to_local
from chatbot_api.models import Conversation, Message, Student, StudentProfile
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
            query = query.where(
                to_local(Conversation.opened_at) >= datetime.combine(from_date, time.min)
            )
        if to_date is not None:
            query = query.where(
                to_local(Conversation.opened_at) <= datetime.combine(to_date, time.max)
            )
        if phone:
            query = query.join(Student, Conversation.student_id == Student.id)
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
    ) -> list[tuple[Conversation, int, str | None, str | None, datetime | None]]:
        """Single query: (Conversation, message_count, last_message_preview,
        profile_name, last_message_at).

        Orden por última actividad (estilo WhatsApp/Chatwoot): como hay un solo
        hilo por contacto que se reabre, `opened_at` es la fecha del primer
        contacto y dejaría arriba conversaciones viejas. Sin mensajes cae a
        `opened_at`; `id` desempata para que la paginación sea estable.
        """
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
        last_msg_at_subq = (
            select(func.max(Message.created_at))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        profile_name_subq = (
            select(StudentProfile.full_name)
            .join(Student, Student.phone_e164 == StudentProfile.phone_e164)
            .where(Student.id == Conversation.student_id)
            .correlate(Conversation)
            .scalar_subquery()
        )

        query = select(
            Conversation,
            msg_count_subq.label("message_count"),
            last_msg_subq.label("last_message_content"),
            profile_name_subq.label("profile_name"),
            last_msg_at_subq.label("last_message_at"),
        ).options(selectinload(Conversation.student))
        query = self._apply_filters(
            query, status=status, from_date=from_date, to_date=to_date, phone=phone
        )
        last_activity = func.coalesce(last_msg_at_subq, Conversation.opened_at)
        query = (
            query.order_by(last_activity.desc(), Conversation.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        rows = result.unique().all()
        return [
            (
                row[0],
                int(row.message_count),
                _truncate(row.last_message_content),
                row.profile_name,
                row.last_message_at,
            )
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

    async def count_by_status(self, db: AsyncSession) -> dict[ConversationStatus, int]:
        """Conteo agrupado por estado en una sola query (para los tabs)."""
        result = await db.execute(
            select(Conversation.status, func.count(Conversation.id)).group_by(Conversation.status)
        )
        return {status: int(count) for status, count in result.all()}

    async def count_by_phone(self, db: AsyncSession, phone: str) -> int:
        result = await db.execute(
            select(func.count(Conversation.id)).where(Conversation.student_phone == phone)
        )
        return int(result.scalar_one())

    async def count_messages_by_phone(self, db: AsyncSession, phone: str) -> int:
        result = await db.execute(
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.student_phone == phone)
        )
        return int(result.scalar_one())

    async def count_by_student(self, db: AsyncSession, student_id: int) -> int:
        return int(
            await db.scalar(
                select(func.count(Conversation.id)).where(Conversation.student_id == student_id)
            )
            or 0
        )

    async def count_messages_by_student(self, db: AsyncSession, student_id: int) -> int:
        return int(
            await db.scalar(
                select(func.count(Message.id))
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(Conversation.student_id == student_id)
            )
            or 0
        )

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
    ) -> tuple[Conversation, bool, bool]:
        """Conversación activa del estudiante (modelo estilo Chatwoot).

        Toma la última conversación del número: si está abierta/takeover la
        reutiliza; si está `cerrada` la **reabre** (un solo hilo por contacto,
        sin duplicados en el CRM). Solo crea una nueva en el primer contacto.

        Returns (conversation, created, reopened):
          - created: True solo si se creó una conversación nueva.
          - reopened: True si se reabrió una que estaba `cerrada`.
        """
        from .student import student_repository

        student, _ = await student_repository.upsert_by_phone(db, phone_e164=student_phone)
        return await self.get_or_create_open_for_student(db, student.id)

    async def get_or_create_open_for_student(
        self, db: AsyncSession, student_id: int
    ) -> tuple[Conversation, bool, bool]:
        # Parent row lock serializes first-conversation creation without requiring
        # a uniqueness constraint that would invalidate existing historical rows.
        student = await db.scalar(select(Student).where(Student.id == student_id).with_for_update())
        if student is None:
            raise ValueError("student not found")
        result = await db.execute(
            select(Conversation)
            .where(Conversation.student_id == student_id)
            .order_by(Conversation.opened_at.desc())
            .limit(1)
        )
        latest = result.scalars().first()
        if latest is not None:
            if latest.status == ConversationStatus.cerrada:
                latest.status = ConversationStatus.abierta
                latest.closed_at = None
                latest.closed_by = None
                await db.flush()
                return latest, False, True
            return latest, False, False
        conv = Conversation(
            student_id=student_id,
            student_phone=student.phone_e164,
            status=ConversationStatus.abierta,
        )
        db.add(conv)
        await db.flush()
        return conv, True, False


conversation_repository = ConversationRepository(Conversation)
