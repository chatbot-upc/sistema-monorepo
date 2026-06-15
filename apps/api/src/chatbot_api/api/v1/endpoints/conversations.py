from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.models.enums import ConversationStatus
from chatbot_api.schemas.conversation import (
    ContactUpdate,
    ConversationDetail,
    ConversationHistory,
    ConversationListItem,
    SendMessageRequest,
    SendMessageResponse,
    StarUpdate,
)
from chatbot_api.schemas.internal_note import NoteCreate, NoteRead, NoteUpdate
from chatbot_api.schemas.message import MessageRead
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.schemas.tag import TagAssign
from chatbot_api.services import conversation_service, note_service, tag_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=Page[ConversationListItem])
async def list_conversations(
    status_filter: ConversationStatus | None = Query(None, alias="status"),
    from_date: date | None = None,
    to_date: date | None = None,
    phone: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> Page[ConversationListItem]:
    return await conversation_service.list_paginated(
        db,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        phone=phone,
        pagination=PageParams(page=page, size=size),
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    return await conversation_service.get_detail(db, conversation_id)


@router.get("/{conversation_id}/messages", response_model=Page[MessageRead])
async def list_messages(
    conversation_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> Page[MessageRead]:
    return await conversation_service.list_messages_paginated(
        db, conversation_id, pagination=PageParams(page=page, size=size)
    )


@router.post("/{conversation_id}/takeover")
async def takeover(
    conversation_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return await conversation_service.takeover(
        db, conversation_id=conversation_id, admin_id=admin.id
    )


@router.post("/{conversation_id}/release")
async def release(
    conversation_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return await conversation_service.release(
        db, conversation_id=conversation_id, admin_id=admin.id
    )


@router.post("/{conversation_id}/close")
async def close(
    conversation_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return await conversation_service.close(
        db, conversation_id=conversation_id, admin_id=admin.id
    )


@router.post("/{conversation_id}/reopen")
async def reopen(
    conversation_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return await conversation_service.reopen(
        db, conversation_id=conversation_id, admin_id=admin.id
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> None:
    await conversation_service.delete_conversation(
        db, conversation_id=conversation_id, admin_id=admin.id
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: int,
    payload: SendMessageRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> SendMessageResponse:
    return await conversation_service.send_admin_message(
        db,
        conversation_id=conversation_id,
        body=payload.body,
        admin_id=admin.id,
        in_reply_to_id=payload.in_reply_to_id,
    )


# ── Ficha de contacto: correo, destacar, historial ────────────────────


@router.get("/{conversation_id}/history", response_model=ConversationHistory)
async def get_history(
    conversation_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> ConversationHistory:
    return await conversation_service.get_history(db, conversation_id)


@router.patch("/{conversation_id}/contact", response_model=ConversationDetail)
async def update_contact(
    conversation_id: int,
    payload: ContactUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    return await conversation_service.update_contact(
        db, conversation_id=conversation_id, email=payload.email
    )


@router.put("/{conversation_id}/star", response_model=ConversationDetail)
async def set_star(
    conversation_id: int,
    payload: StarUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    return await conversation_service.set_starred(
        db, conversation_id=conversation_id, starred=payload.starred
    )


# ── Etiquetas de la conversación ──────────────────────────────────────


@router.post("/{conversation_id}/tags", response_model=ConversationDetail)
async def assign_tag(
    conversation_id: int,
    payload: TagAssign,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    return await tag_service.assign_tag(
        db, conversation_id=conversation_id, tag_id=payload.tag_id
    )


@router.delete("/{conversation_id}/tags/{tag_id}", response_model=ConversationDetail)
async def unassign_tag(
    conversation_id: int,
    tag_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    return await tag_service.unassign_tag(
        db, conversation_id=conversation_id, tag_id=tag_id
    )


# ── Notas internas ────────────────────────────────────────────────────


@router.get("/{conversation_id}/notes", response_model=list[NoteRead])
async def list_notes(
    conversation_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> list[NoteRead]:
    return await note_service.list_notes(db, conversation_id)


@router.post(
    "/{conversation_id}/notes",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    conversation_id: int,
    payload: NoteCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> NoteRead:
    return await note_service.create_note(
        db, conversation_id=conversation_id, author=admin, body=payload.body
    )


@router.patch("/{conversation_id}/notes/{note_id}", response_model=NoteRead)
async def update_note(
    conversation_id: int,
    note_id: int,
    payload: NoteUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> NoteRead:
    return await note_service.update_note(
        db, conversation_id=conversation_id, note_id=note_id, body=payload.body
    )


@router.delete(
    "/{conversation_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_note(
    conversation_id: int,
    note_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> None:
    await note_service.delete_note(
        db, conversation_id=conversation_id, note_id=note_id
    )
