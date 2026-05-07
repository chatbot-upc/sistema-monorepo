from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.models.enums import ConversationStatus
from chatbot_api.schemas.conversation import ConversationDetail, ConversationListItem
from chatbot_api.schemas.message import MessageRead
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.services.conversation_service import conversation_service

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
    result = await conversation_service.get_detail(db, conversation_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return result


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


@router.post("/{conversation_id}/takeover", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def takeover(conversation_id: int, _: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 4")


@router.post("/{conversation_id}/release", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def release(conversation_id: int, _: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 4")


@router.post("/{conversation_id}/close", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def close(conversation_id: int, _: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 4")


@router.post("/{conversation_id}/reopen", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def reopen(conversation_id: int, _: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 4")


@router.post("/{conversation_id}/messages", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def send_message(
    conversation_id: int, _: Admin = Depends(get_current_admin)
) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 4")
