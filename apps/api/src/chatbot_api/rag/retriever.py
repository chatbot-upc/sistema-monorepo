"""Retrieval contra document_chunks vía pgvector cosine distance."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Document, DocumentChunk
from chatbot_api.models.enums import DocumentStatus

from .embeddings import get_embeddings


async def retrieve(
    db: AsyncSession,
    query: str,
    *,
    k: int = 5,
    fetch_k: int = 20,
    metadata_filter: dict[str, str] | None = None,
) -> list[tuple[DocumentChunk, float]]:
    """Devuelve (chunk, cosine_distance). distance ∈ [0, 2]; 0 = idéntico."""
    embeddings = get_embeddings()
    query_vec = await embeddings.aembed_query(query)
    distance = DocumentChunk.embedding.cosine_distance(query_vec).label("distance")

    stmt = (
        select(DocumentChunk, distance)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.status == DocumentStatus.indexed)
    )
    if metadata_filter:
        for key, value in metadata_filter.items():
            stmt = stmt.where(DocumentChunk.meta[key].astext == str(value))
    stmt = stmt.order_by(distance).limit(fetch_k)

    rows = (await db.execute(stmt)).all()
    return [(row[0], float(row.distance)) for row in rows[:k]]
