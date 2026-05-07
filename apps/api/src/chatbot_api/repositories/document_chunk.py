from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import DocumentChunk

from .base import BaseRepository


class _ChunkCreate(BaseModel):
    pass


class _ChunkUpdate(BaseModel):
    pass


class DocumentChunkRepository(BaseRepository[DocumentChunk, _ChunkCreate, _ChunkUpdate]):
    async def bulk_insert(
        self,
        db: AsyncSession,
        document_id: int,
        chunks: list[dict[str, Any]],
    ) -> int:
        """chunks: [{chunk_text, embedding, meta, chunk_index}]. Devuelve count."""
        if not chunks:
            return 0
        objs = [DocumentChunk(document_id=document_id, **c) for c in chunks]
        db.add_all(objs)
        await db.flush()
        return len(objs)

    async def delete_by_document(self, db: AsyncSession, document_id: int) -> int:
        result = await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]


document_chunk_repository = DocumentChunkRepository(DocumentChunk)
