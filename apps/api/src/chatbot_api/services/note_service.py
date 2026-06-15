"""Notas internas del asesor por conversación (CRUD)."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Admin, InternalNote
from chatbot_api.repositories.internal_note import internal_note_repository
from chatbot_api.schemas.internal_note import NoteRead


def _to_read(note: InternalNote) -> NoteRead:
    return NoteRead(
        id=note.id,
        body=note.body,
        author_admin_id=note.author_admin_id,
        author_name=note.author.name if note.author else None,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


async def list_notes(db: AsyncSession, conversation_id: int) -> list[NoteRead]:
    notes = await internal_note_repository.list_by_conversation(db, conversation_id)
    return [_to_read(n) for n in notes]


async def create_note(
    db: AsyncSession, *, conversation_id: int, author: Admin, body: str
) -> NoteRead:
    note = await internal_note_repository.create(
        db,
        conversation_id=conversation_id,
        author_admin_id=author.id,
        body=body.strip(),
    )
    await db.commit()
    # `author` ya lo tenemos en mano; evita un lazy-load tras el commit.
    return NoteRead(
        id=note.id,
        body=note.body,
        author_admin_id=author.id,
        author_name=author.name,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


async def _get_owned_or_404(
    db: AsyncSession, conversation_id: int, note_id: int
) -> InternalNote:
    note = await internal_note_repository.get(db, note_id)
    if note is None or note.conversation_id != conversation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "note not found")
    return note


async def update_note(
    db: AsyncSession, *, conversation_id: int, note_id: int, body: str
) -> NoteRead:
    note = await _get_owned_or_404(db, conversation_id, note_id)
    note.body = body.strip()
    await db.commit()
    await db.refresh(note)
    return _to_read(note)


async def delete_note(
    db: AsyncSession, *, conversation_id: int, note_id: int
) -> None:
    note = await _get_owned_or_404(db, conversation_id, note_id)
    await db.delete(note)
    await db.commit()
