from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import (
    Admin,
    AdminRole,
    Conversation,
    ConversationStatus,
    Document,
    DocumentChunk,
    DocumentSourceType,
    DocumentStatus,
    Intent,
    Message,
    MessageRole,
    Student,
)


async def test_create_admin(db_session: AsyncSession) -> None:
    admin = Admin(email="alice@upc.edu.pe", name="Alice", role=AdminRole.admin)
    db_session.add(admin)
    await db_session.flush()

    assert admin.id is not None
    assert admin.role == AdminRole.admin
    assert admin.active is True


async def test_create_conversation_with_student(db_session: AsyncSession) -> None:
    student = Student(phone_e164="+51900000001", display_name="Juan")
    db_session.add(student)
    await db_session.flush()

    conv = Conversation(student_phone=student.phone_e164, status=ConversationStatus.abierta)
    db_session.add(conv)
    await db_session.flush()

    result = await db_session.execute(
        select(Conversation).where(Conversation.id == conv.id)
    )
    loaded = result.scalar_one()
    assert loaded.student.display_name == "Juan"
    assert loaded.status == ConversationStatus.abierta


async def test_message_belongs_to_conversation(db_session: AsyncSession) -> None:
    student = Student(phone_e164="+51900000002")
    db_session.add(student)
    conv = Conversation(student_phone=student.phone_e164)
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.student,
        content="Hola",
    )
    db_session.add(msg)
    await db_session.flush()

    assert msg.id is not None
    assert msg.conversation_id == conv.id


async def test_document_chunk_embedding(db_session: AsyncSession) -> None:
    doc = Document(
        title="Calendario 2026",
        source_type=DocumentSourceType.upload,
        s3_key="docs/cal-2026.pdf",
        sha256="a" * 64,
        status=DocumentStatus.indexed,
    )
    db_session.add(doc)
    await db_session.flush()

    embedding = [0.1] * 1536
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_text="Matrícula del 1 al 15 de marzo",
        embedding=embedding,
        chunk_index=0,
    )
    db_session.add(chunk)
    await db_session.flush()

    result = await db_session.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk.id)
    )
    loaded = result.scalar_one()
    assert len(loaded.embedding) == 1536
    assert loaded.chunk_text.startswith("Matrícula")


async def test_intent_unique_name(db_session: AsyncSession) -> None:
    db_session.add(Intent(name="duplicate_test", description="first"))
    await db_session.flush()

    db_session.add(Intent(name="duplicate_test", description="second"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_seed_data_present(db_session: AsyncSession) -> None:
    result = await db_session.execute(select(Admin).where(Admin.email == "dev@upc.edu.pe"))
    admin = result.scalar_one_or_none()
    assert admin is not None
    assert admin.role == AdminRole.admin

    result = await db_session.execute(select(Intent.name))
    names = {row[0] for row in result.all()}
    assert {"consulta_fechas", "consulta_costos", "consulta_becas"} <= names


async def test_conversation_timestamps(db_session: AsyncSession) -> None:
    student = Student(phone_e164="+51900000003")
    db_session.add(student)
    conv = Conversation(student_phone=student.phone_e164)
    db_session.add(conv)
    await db_session.flush()
    await db_session.refresh(conv)

    assert isinstance(conv.opened_at, datetime)
    assert isinstance(conv.created_at, datetime)
