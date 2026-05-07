from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import NotificationStatus
from chatbot_api.repositories.notification import notification_repository
from chatbot_api.schemas.notification import NotificationRead
from chatbot_api.schemas.pagination import Page, PageParams


class NotificationService:
    def __init__(self) -> None:
        self.repository = notification_repository

    async def list_paginated(
        self,
        db: AsyncSession,
        *,
        status: NotificationStatus | None = None,
        pagination: PageParams,
    ) -> Page[NotificationRead]:
        rows = await self.repository.list_filtered(
            db, status=status, skip=pagination.offset, limit=pagination.size
        )
        total = await self.repository.count_filtered(db, status=status)
        items = [NotificationRead.model_validate(n) for n in rows]
        return Page(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=ceil(total / pagination.size) if total else 0,
        )


notification_service = NotificationService()
