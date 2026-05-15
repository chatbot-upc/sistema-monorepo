from typing import Any

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
        query: Select[Any],
        *,
        status: DocumentStatus | None,
        source_type: DocumentSourceType | None,
    ) -> Select[Any]:
        if status is not None:
            query = query.where(Document.status == status)
        if source_type is not None:
            query = query.where(Document.source_type == source_type)
        return query

    async def list_filtered_with_chunk_count(
        self,
        db: AsyncSession,
        *,
        status: DocumentStatus | None = None,
        source_type: DocumentSourceType | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[tuple[Document, int]]:
        chunk_count_subq = (
            select(func.count(DocumentChunk.id))
            .where(DocumentChunk.document_id == Document.id)
            .correlate(Document)
            .scalar_subquery()
        )
        query = select(Document, chunk_count_subq.label("chunk_count"))
        query = self._apply_filters(query, status=status, source_type=source_type)
        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return [(row[0], int(row.chunk_count)) for row in result.all()]

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

    async def status_summary(
        self, db: AsyncSession
    ) -> tuple[dict[DocumentStatus, int], int, int]:
        """Aggregate counts across every document for the admin dashboard.

        Returns (counts_by_status, total_documents, total_chunks).
        Single SQL trip — avoids fanning out one count query per status.
        """
        status_query = select(Document.status, func.count(Document.id)).group_by(
            Document.status
        )
        status_result = await db.execute(status_query)
        counts: dict[DocumentStatus, int] = {s: 0 for s in DocumentStatus}
        total = 0
        for status_value, count in status_result.all():
            counts[status_value] = int(count)
            total += int(count)

        chunks_result = await db.execute(select(func.count(DocumentChunk.id)))
        total_chunks = int(chunks_result.scalar_one())

        return counts, total, total_chunks

    async def get_by_sha256(self, db: AsyncSession, sha256: str) -> Document | None:
        result = await db.execute(select(Document).where(Document.sha256 == sha256))
        return result.scalars().first()


document_repository = DocumentRepository(Document)
