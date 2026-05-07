from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import DocumentSourceType, DocumentStatus
from chatbot_api.repositories.document import document_repository
from chatbot_api.schemas.document import DocumentRead
from chatbot_api.schemas.pagination import Page, PageParams


class DocumentService:
    def __init__(self) -> None:
        self.repository = document_repository

    async def list_paginated(
        self,
        db: AsyncSession,
        *,
        status: DocumentStatus | None = None,
        source_type: DocumentSourceType | None = None,
        pagination: PageParams,
    ) -> Page[DocumentRead]:
        rows = await self.repository.list_filtered(
            db,
            status=status,
            source_type=source_type,
            skip=pagination.offset,
            limit=pagination.size,
        )
        total = await self.repository.count_filtered(
            db, status=status, source_type=source_type
        )

        items: list[DocumentRead] = []
        for doc in rows:
            chunks = await self.repository.chunk_count(db, doc.id)
            item = DocumentRead.model_validate(doc)
            items.append(item.model_copy(update={"chunk_count": chunks}))

        return Page(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=ceil(total / pagination.size) if total else 0,
        )

    async def get_detail(self, db: AsyncSession, document_id: int) -> DocumentRead | None:
        doc = await self.repository.get(db, document_id)
        if doc is None:
            return None
        chunks = await self.repository.chunk_count(db, doc.id)
        return DocumentRead.model_validate(doc).model_copy(update={"chunk_count": chunks})


document_service = DocumentService()
