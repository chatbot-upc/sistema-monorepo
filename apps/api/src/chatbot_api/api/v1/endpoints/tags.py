from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.schemas.tag import TagCreate, TagRead
from chatbot_api.services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def list_tags(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> list[TagRead]:
    return await tag_service.list_tags(db)


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> TagRead:
    return await tag_service.create_tag(db, name=payload.name, color=payload.color)
