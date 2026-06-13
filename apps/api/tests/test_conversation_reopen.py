"""Modelo Chatwoot: una conversación cerrada se reabre al escribir el estudiante
(en vez de crear una nueva → sin duplicados por número en el CRM)."""

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.conversation import conversation_repository

from . import factories


async def test_reopens_closed_conversation(db_session: AsyncSession) -> None:
    student = await factories.make_student(db_session, phone="+51900700001")
    closed = await factories.make_conversation(
        db_session,
        student_phone=student.phone_e164,
        status=ConversationStatus.cerrada,
    )
    closed_id = closed.id

    conv, created, reopened = await conversation_repository.get_or_create_open(
        db_session, student.phone_e164
    )
    assert conv.id == closed_id  # mismo hilo, no uno nuevo
    assert created is False
    assert reopened is True
    assert conv.status == ConversationStatus.abierta
    assert conv.closed_at is None
    assert conv.closed_by is None


async def test_reuses_open_conversation(db_session: AsyncSession) -> None:
    student = await factories.make_student(db_session, phone="+51900700002")
    opened = await factories.make_conversation(
        db_session,
        student_phone=student.phone_e164,
        status=ConversationStatus.abierta,
    )

    conv, created, reopened = await conversation_repository.get_or_create_open(
        db_session, student.phone_e164
    )
    assert conv.id == opened.id
    assert created is False
    assert reopened is False


async def test_creates_on_first_contact(db_session: AsyncSession) -> None:
    await factories.make_student(db_session, phone="+51900700003")
    conv, created, reopened = await conversation_repository.get_or_create_open(
        db_session, "+51900700003"
    )
    assert created is True
    assert reopened is False
    assert conv.status == ConversationStatus.abierta
