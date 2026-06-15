"""Retrieval contra document_chunks vía pgvector cosine distance."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    program: str | None = None,
) -> list[tuple[DocumentChunk, float]]:
    """Devuelve (chunk, cosine_distance). distance ∈ [0, 2]; 0 = idéntico.

    `program`: si se pasa, scopea por carrera (fix SW-46). Incluye solo docs
    generales (`program IS NULL`) + los de esa carrera → evita mezclar mallas.
    Fail-open: con `program=None` no filtra (comportamiento histórico).
    """
    embeddings = get_embeddings()
    query_vec = await embeddings.aembed_query(query)
    distance = DocumentChunk.embedding.cosine_distance(query_vec).label("distance")

    stmt = (
        select(DocumentChunk, distance)
        .join(Document, Document.id == DocumentChunk.document_id)
        # Eager-load el Document para poder citar su título (nombre del PDF) sin
        # un lazy-load async por chunk en la tool. Una query extra, no N+1.
        .options(selectinload(DocumentChunk.document))
        .where(Document.status == DocumentStatus.indexed)
    )
    if program is not None:
        stmt = stmt.where(
            or_(Document.program.is_(None), Document.program == program)
        )
    if metadata_filter:
        for key, value in metadata_filter.items():
            stmt = stmt.where(DocumentChunk.meta[key].astext == str(value))
    stmt = stmt.order_by(distance).limit(fetch_k)

    rows = (await db.execute(stmt)).all()
    return [(row[0], float(row.distance)) for row in rows[:k]]
