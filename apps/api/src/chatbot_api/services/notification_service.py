"""Business logic for notifications. Functional module (RORO), no classes."""

from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import NotificationStatus
from chatbot_api.repositories.notification import notification_repository
from chatbot_api.schemas.notification import NotificationRead
from chatbot_api.schemas.pagination import Page, PageParams


async def list_paginated(
    db: AsyncSession,
    *,
    status: NotificationStatus | None = None,
    pagination: PageParams,
) -> Page[NotificationRead]:
    rows = await notification_repository.list_filtered(
        db, status=status, skip=pagination.offset, limit=pagination.size
    )
    total = await notification_repository.count_filtered(db, status=status)
    items = [NotificationRead.model_validate(n) for n in rows]
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )
