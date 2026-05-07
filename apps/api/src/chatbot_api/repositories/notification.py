from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Notification
from chatbot_api.models.enums import NotificationStatus

from .base import BaseRepository


class _NotifCreate(BaseModel):
    pass


class _NotifUpdate(BaseModel):
    pass


class NotificationRepository(BaseRepository[Notification, _NotifCreate, _NotifUpdate]):
    def _apply_filters(
        self,
        query: Select[tuple[Notification]],
        *,
        status: NotificationStatus | None,
    ) -> Select[tuple[Notification]]:
        if status is not None:
            query = query.where(Notification.status == status)
        return query

    async def list_filtered(
        self,
        db: AsyncSession,
        *,
        status: NotificationStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Notification]:
        query: Select[tuple[Notification]] = select(Notification)
        query = self._apply_filters(query, status=status)
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        status: NotificationStatus | None = None,
    ) -> int:
        query: Select[tuple[Notification]] = select(Notification)
        query = self._apply_filters(query, status=status)
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        return int(result.scalar_one())


notification_repository = NotificationRepository(Notification)
