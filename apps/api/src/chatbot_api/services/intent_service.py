from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.repositories.intent import intent_repository
from chatbot_api.schemas.intent import IntentRead
from chatbot_api.schemas.pagination import Page, PageParams


class IntentService:
    def __init__(self) -> None:
        self.repository = intent_repository

    async def list_paginated(
        self,
        db: AsyncSession,
        *,
        active: bool | None = None,
        pagination: PageParams,
    ) -> Page[IntentRead]:
        rows = await self.repository.list_filtered(
            db, active=active, skip=pagination.offset, limit=pagination.size
        )
        total = await self.repository.count_filtered(db, active=active)
        items = [IntentRead.model_validate(i) for i in rows]
        return Page(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=ceil(total / pagination.size) if total else 0,
        )

    async def get_detail(self, db: AsyncSession, intent_id: int) -> IntentRead | None:
        intent = await self.repository.get(db, intent_id)
        if intent is None:
            return None
        return IntentRead.model_validate(intent)


intent_service = IntentService()
