from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Intent

from .base import BaseRepository


class _IntentCreate(BaseModel):
    pass


class _IntentUpdate(BaseModel):
    pass


class IntentRepository(BaseRepository[Intent, _IntentCreate, _IntentUpdate]):
    def _apply_filters(
        self,
        query: Select[tuple[Intent]],
        *,
        active: bool | None,
    ) -> Select[tuple[Intent]]:
        if active is not None:
            query = query.where(Intent.active == active)
        return query

    async def list_filtered(
        self,
        db: AsyncSession,
        *,
        active: bool | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Intent]:
        query: Select[tuple[Intent]] = select(Intent)
        query = self._apply_filters(query, active=active)
        query = query.order_by(Intent.name.asc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        active: bool | None = None,
    ) -> int:
        query: Select[tuple[Intent]] = select(Intent)
        query = self._apply_filters(query, active=active)
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        return int(result.scalar_one())

    async def get_by_name(self, db: AsyncSession, name: str) -> Intent | None:
        result = await db.execute(select(Intent).where(Intent.name == name))
        return result.scalars().first()


intent_repository = IntentRepository(Intent)
