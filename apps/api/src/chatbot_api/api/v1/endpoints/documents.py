from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.models.enums import DocumentSourceType, DocumentStatus
from chatbot_api.schemas.document import DocumentRead
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=Page[DocumentRead])
async def list_documents(
    status_filter: DocumentStatus | None = Query(None, alias="status"),
    source_type: DocumentSourceType | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> Page[DocumentRead]:
    return await document_service.list_paginated(
        db,
        status=status_filter,
        source_type=source_type,
        pagination=PageParams(page=page, size=size),
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> DocumentRead:
    return await document_service.get_detail(db, document_id)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload(
    file: UploadFile = File(...),
    source_type: DocumentSourceType = Form(DocumentSourceType.upload),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> DocumentRead:
    content = await file.read()
    return await document_service.upload_document(
        db,
        filename=file.filename or "untitled.pdf",
        content=content,
        source_type=source_type,
        uploaded_by=admin.id,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> None:
    await document_service.delete_document(db, document_id)
