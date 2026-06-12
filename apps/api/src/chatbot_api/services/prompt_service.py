"""Business logic for prompt versions (SW-54). Functional module (RORO)."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import PromptVersion
from chatbot_api.repositories.prompt_version import prompt_version_repository
from chatbot_api.schemas.prompt import (
    PromptVersionCreate,
    PromptVersionRead,
    PromptVersionUpdate,
)
from chatbot_api.services import rag_service

_PROMPT_NAME = "agent_system"


async def list_versions(db: AsyncSession) -> list[PromptVersionRead]:
    rows = await prompt_version_repository.list_by_name(db, _PROMPT_NAME)
    return [PromptVersionRead.model_validate(r) for r in rows]


async def create_version(
    db: AsyncSession, *, payload: PromptVersionCreate, admin_id: int
) -> PromptVersionRead:
    next_version = await prompt_version_repository.max_version(db, _PROMPT_NAME) + 1
    version = PromptVersion(
        name=_PROMPT_NAME,
        version=next_version,
        content=payload.content,
        active=False,
        created_by=admin_id,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return PromptVersionRead.model_validate(version)


async def update_version(
    db: AsyncSession, *, version_id: int, payload: PromptVersionUpdate
) -> PromptVersionRead:
    version = await prompt_version_repository.get(db, version_id)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "prompt version not found")
    version.content = payload.content
    await db.commit()
    await db.refresh(version)
    # Editar la versión activa cambia lo que ve el bot → invalidar cache.
    if version.active:
        await rag_service.bump_prompt_generation()
    return PromptVersionRead.model_validate(version)


async def activate_version(
    db: AsyncSession, *, version_id: int
) -> PromptVersionRead:
    version = await prompt_version_repository.get(db, version_id)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "prompt version not found")
    await prompt_version_repository.deactivate_all(db, version.name)
    version.active = True
    await db.commit()
    await db.refresh(version)
    await rag_service.bump_prompt_generation()
    return PromptVersionRead.model_validate(version)


async def delete_version(db: AsyncSession, *, version_id: int) -> None:
    version = await prompt_version_repository.get(db, version_id)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "prompt version not found")
    if version.active:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "no se puede eliminar la versión activa; activa otra primero",
        )
    await db.delete(version)
    await db.commit()
