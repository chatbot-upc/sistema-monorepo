"""Catálogo global de etiquetas y su asignación a conversaciones."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.tag import tag_repository
from chatbot_api.schemas.conversation import ConversationDetail
from chatbot_api.schemas.tag import TagRead
from chatbot_api.services import conversation_service


async def list_tags(db: AsyncSession) -> list[TagRead]:
    tags = await tag_repository.list_all(db)
    return [TagRead.model_validate(t) for t in tags]


async def create_tag(db: AsyncSession, *, name: str, color: str) -> TagRead:
    name = name.strip()
    existing = await tag_repository.get_by_name(db, name)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "ya existe una etiqueta con ese nombre")
    tag = await tag_repository.create(db, name=name, color=color)
    await db.commit()
    return TagRead.model_validate(tag)


async def assign_tag(
    db: AsyncSession, *, conversation_id: int, tag_id: int
) -> ConversationDetail:
    conv = await conversation_repository.get(db, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    tag = await tag_repository.get(db, tag_id)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "tag not found")
    if all(t.id != tag_id for t in conv.tags):
        conv.tags.append(tag)
        await db.commit()
    return await conversation_service.get_detail(db, conversation_id)


async def unassign_tag(
    db: AsyncSession, *, conversation_id: int, tag_id: int
) -> ConversationDetail:
    conv = await conversation_repository.get(db, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    keep = [t for t in conv.tags if t.id != tag_id]
    if len(keep) != len(conv.tags):
        conv.tags[:] = keep
        await db.commit()
    return await conversation_service.get_detail(db, conversation_id)
