from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import InternalNote


class InternalNoteRepository:
    async def list_by_conversation(
        self, db: AsyncSession, conversation_id: int
    ) -> list[InternalNote]:
        result = await db.execute(
            select(InternalNote)
            .where(InternalNote.conversation_id == conversation_id)
            .order_by(InternalNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, note_id: int) -> InternalNote | None:
        result = await db.execute(
            select(InternalNote).where(InternalNote.id == note_id)
        )
        return result.scalars().first()

    async def create(
        self,
        db: AsyncSession,
        *,
        conversation_id: int,
        author_admin_id: int | None,
        body: str,
    ) -> InternalNote:
        note = InternalNote(
            conversation_id=conversation_id,
            author_admin_id=author_admin_id,
            body=body,
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)
        return note


internal_note_repository = InternalNoteRepository()
