from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.models.enums import NotificationStatus
from chatbot_api.schemas.notification import NotificationRead
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    status_filter: NotificationStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> Page[NotificationRead]:
    return await notification_service.list_paginated(
        db, status=status_filter, pagination=PageParams(page=page, size=size)
    )


@router.get("/templates")
async def list_templates(_: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED, "Meta templates fetch en Fase 4"
    )


@router.post("")
async def create_notification(_: Admin = Depends(get_current_admin)) -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "implementado en Fase 4")
