from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.models.enums import ConversationStatus
from chatbot_api.schemas.conversation import (
    ConversationDetail,
    ConversationListItem,
    SendMessageRequest,
    SendMessageResponse,
)
from chatbot_api.schemas.message import MessageRead
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.services import conversation_service

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
    )
