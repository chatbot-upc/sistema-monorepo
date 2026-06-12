from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.schemas.prompt import (
    PromptVersionCreate,
    PromptVersionRead,
    PromptVersionUpdate,
)
from chatbot_api.services import prompt_service

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptVersionRead])
async def list_prompt_versions(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> list[PromptVersionRead]:
    return await prompt_service.list_versions(db)


@router.post(
    "", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED
)
async def create_prompt_version(
    payload: PromptVersionCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> PromptVersionRead:
    return await prompt_service.create_version(
        db, payload=payload, admin_id=admin.id
    )


@router.put("/{version_id}", response_model=PromptVersionRead)
async def update_prompt_version(
    version_id: int,
    payload: PromptVersionUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> PromptVersionRead:
    return await prompt_service.update_version(
        db, version_id=version_id, payload=payload
    )


@router.post("/{version_id}/activate", response_model=PromptVersionRead)
async def activate_prompt_version(
    version_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> PromptVersionRead:
    return await prompt_service.activate_version(db, version_id=version_id)


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_version(
    version_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> None:
    await prompt_service.delete_version(db, version_id=version_id)
