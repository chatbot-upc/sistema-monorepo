from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Document, DocumentChunk
from chatbot_api.models.enums import DocumentSourceType, DocumentStatus

from .base import BaseRepository


class _DocCreate(BaseModel):
    pass


class _DocUpdate(BaseModel):
    pass


class DocumentRepository(BaseRepository[Document, _DocCreate, _DocUpdate]):
    def _apply_filters(
        self,
        query: Select[tuple[Document]],
        *,
        status: DocumentStatus | None,
        source_type: DocumentSourceType | None,
    ) -> Select[tuple[Document]]:
        if status is not None:
            query = query.where(Document.status == status)
        if source_type is not None:
            query = query.where(Document.source_type == source_type)
        return query

    async def list_filtered(
        self,
        db: AsyncSession,
        *,
        status: DocumentStatus | None = None,
        source_type: DocumentSourceType | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Document]:
        query: Select[tuple[Document]] = select(Document)
        query = self._apply_filters(query, status=status, source_type=source_type)
        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        status: DocumentStatus | None = None,
        source_type: DocumentSourceType | None = None,
    ) -> int:
        query: Select[tuple[Document]] = select(Document)
        query = self._apply_filters(query, status=status, source_type=source_type)
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        return int(result.scalar_one())

    async def chunk_count(self, db: AsyncSession, document_id: int) -> int:
        result = await db.execute(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == document_id
            )
        )
        return int(result.scalar_one())


document_repository = DocumentRepository(Document)
