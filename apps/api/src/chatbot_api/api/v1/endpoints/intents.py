from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.schemas.intent import IntentRead
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.services.intent_service import intent_service

router = APIRouter(prefix="/intents", tags=["intents"])


@router.get("", response_model=Page[IntentRead])
async def list_intents(
    active: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> Page[IntentRead]:
    return await intent_service.list_paginated(
        db, active=active, pagination=PageParams(page=page, size=size)
    )


@router.get("/{intent_id}", response_model=IntentRead)
async def get_intent(
    intent_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> IntentRead:
    result = await intent_service.get_detail(db, intent_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "intent not found")
    return result


@router.post("")
async def create_intent(_: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 5")


@router.put("/{intent_id}")
async def update_intent(intent_id: int, _: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 5")


@router.delete("/{intent_id}")
async def delete_intent(intent_id: int, _: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 5")
