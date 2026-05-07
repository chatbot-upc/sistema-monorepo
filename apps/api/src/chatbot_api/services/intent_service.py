"""Business logic for intents. Functional module (RORO), no classes."""

from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.repositories.intent import intent_repository
from chatbot_api.schemas.intent import IntentRead
from chatbot_api.schemas.pagination import Page, PageParams


async def list_paginated(
    db: AsyncSession,
    *,
    active: bool | None = None,
    pagination: PageParams,
) -> Page[IntentRead]:
    rows = await intent_repository.list_filtered(
        db, active=active, skip=pagination.offset, limit=pagination.size
    )
    total = await intent_repository.count_filtered(db, active=active)
    items = [IntentRead.model_validate(i) for i in rows]
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )


async def get_detail(db: AsyncSession, intent_id: int) -> IntentRead:
    intent = await intent_repository.get(db, intent_id)
    if intent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "intent not found")
    return IntentRead.model_validate(intent)
