"""Helpers to insert test data fixtures."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import (
    Admin,
    AdminRole,
    Conversation,
    ConversationStatus,
    Document,
    DocumentSourceType,
    DocumentStatus,
    Intent,
    Message,
    MessageRole,
    Student,
)


async def make_admin(
    db: AsyncSession,
    *,
    email: str = "alice@upc.edu.pe",
    name: str = "Alice",
    role: AdminRole = AdminRole.admin,
    active: bool = True,
) -> Admin:
    admin = Admin(email=email, name=name, role=role, active=active)
    db.add(admin)
    await db.flush()
    return admin


async def make_student(
    db: AsyncSession,
    *,
    phone: str = "+51900000001",
    display_name: str | None = "Maria Paula",
) -> Student:
    student = Student(phone_e164=phone, display_name=display_name)
    db.add(student)
    await db.flush()
    return student


async def make_conversation(
    db: AsyncSession,
    *,
    student_phone: str,
    status: ConversationStatus = ConversationStatus.abierta,
    opened_at: datetime | None = None,
) -> Conversation:
    conv = Conversation(
        student_phone=student_phone,
        status=status,
        opened_at=opened_at or datetime.now()
    )
    db.add(conv)
    await db.flush()
    return conv


async def make_message(
    db: AsyncSession,
    *,
    conversation_id: int,
    role: MessageRole = MessageRole.student,
    content: str = "hola",
    minutes_ago: int = 0,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        retrieved_chunks=[],
        created_at=datetime.now()
    )
    db.add(msg)
    await db.flush()
    return msg


async def make_document(
    db: AsyncSession,
    *,
    title: str = "Calendario 2026",
    sha256: str = "a" * 64,
    status: DocumentStatus = DocumentStatus.indexed,
    source_type: DocumentSourceType = DocumentSourceType.upload,
) -> Document:
    doc = Document(
        title=title,
        source_type=source_type,
        s3_key=f"docs/{title.lower().replace(' ', '-')}.pdf",
        sha256=sha256,
        status=status,
    )
    db.add(doc)
    await db.flush()
    return doc


async def make_intent(
    db: AsyncSession,
    *,
    name: str = "test_intent",
    description: str | None = None,
    active: bool = True,
) -> Intent:
    intent = Intent(name=name, description=description, examples=[], active=active)
    db.add(intent)
    await db.flush()
    return intent
