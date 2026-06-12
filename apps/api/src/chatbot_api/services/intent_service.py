"""Business logic for intents. Functional module (RORO), no classes."""

from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Intent
from chatbot_api.repositories.intent import intent_repository
from chatbot_api.schemas.intent import IntentCreate, IntentRead, IntentUpdate
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.services import intent_classifier_service


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


async def create_intent(
    db: AsyncSession, *, payload: IntentCreate, admin_id: int
) -> IntentRead:
    existing = await intent_repository.get_by_name(db, payload.name)
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"intent '{payload.name}' ya existe"
        )
    intent = Intent(
        name=payload.name,
        description=payload.description,
        examples=list(payload.examples),
        active=True,
        created_by=admin_id,
    )
    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    await intent_classifier_service.bump_index_generation()
    return IntentRead.model_validate(intent)


async def update_intent(
    db: AsyncSession, *, intent_id: int, payload: IntentUpdate
) -> IntentRead:
    intent = await intent_repository.get(db, intent_id)
    if intent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "intent not found")
    # `name` es inmutable (clave técnica usada en routing determinista del worker).
    if payload.description is not None:
        intent.description = payload.description
    if payload.examples is not None:
        intent.examples = list(payload.examples)
    if payload.active is not None:
        intent.active = payload.active
    await db.commit()
    await db.refresh(intent)
    await intent_classifier_service.bump_index_generation()
    return IntentRead.model_validate(intent)


async def delete_intent(db: AsyncSession, *, intent_id: int) -> None:
    intent = await intent_repository.get(db, intent_id)
    if intent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "intent not found")
    await db.delete(intent)
    await db.commit()
    await intent_classifier_service.bump_index_generation()
