"""Business logic for documents. Functional module (RORO), no classes."""

import hashlib
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.programs import canonical_program
from chatbot_api.core.storage import get_storage
from chatbot_api.models import Document
from chatbot_api.models.enums import DocumentSourceType, DocumentStatus
from chatbot_api.repositories.document import document_repository
from chatbot_api.schemas.document import (
    DocumentRead,
    DocumentSummary,
    ProgramOption,
)
from chatbot_api.schemas.pagination import Page, PageParams


async def list_program_options(db: AsyncSession) -> list[ProgramOption]:
    """Opciones del selector "Programa/carrera" (SW-46).

    Derivadas de las carreras reales de los estudiantes (audiencias que sí
    scopean). Cada carrera → (slug canónico, etiqueta legible), deduplicado por
    slug y ordenado alfabéticamente. La UI agrega aparte la opción "General".
    """
    from sqlalchemy import select

    from chatbot_api.models import StudentProfile

    rows = (
        await db.execute(
            select(StudentProfile.career)
            .where(StudentProfile.career.is_not(None))
            .distinct()
        )
    ).scalars().all()

    by_slug: dict[str, str] = {}
    for career in rows:
        if career is None:
            continue
        slug = canonical_program(career)
        if slug and slug not in by_slug:
            by_slug[slug] = career
    return [
        ProgramOption(value=slug, label=label)
        for slug, label in sorted(by_slug.items(), key=lambda kv: kv[1].lower())
    ]


async def list_paginated(
    db: AsyncSession,
    *,
    status: DocumentStatus | None = None,
    source_type: DocumentSourceType | None = None,
    pagination: PageParams,
) -> Page[DocumentRead]:
    rows = await document_repository.list_filtered_with_chunk_count(
        db,
        status=status,
        source_type=source_type,
        skip=pagination.offset,
        limit=pagination.size,
    )
    total = await document_repository.count_filtered(
        db, status=status, source_type=source_type
    )

    items = [
        DocumentRead.model_validate(doc).model_copy(update={"chunk_count": chunks})
        for doc, chunks in rows
    ]

    return Page(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )


async def get_detail(db: AsyncSession, document_id: int) -> DocumentRead:
    doc = await document_repository.get(db, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    chunks = await document_repository.chunk_count(db, doc.id)
    return DocumentRead.model_validate(doc).model_copy(update={"chunk_count": chunks})


async def get_summary(db: AsyncSession) -> DocumentSummary:
    counts, total, total_chunks = await document_repository.status_summary(db)
    return DocumentSummary(
        total=total,
        total_chunks=total_chunks,
        indexed=counts[DocumentStatus.indexed],
        indexing=counts[DocumentStatus.indexing],
        pending=counts[DocumentStatus.pending],
        error=counts[DocumentStatus.error],
    )


async def upload_document(
    db: AsyncSession,
    *,
    filename: str,
    content: bytes,
    source_type: DocumentSourceType,
    uploaded_by: int | None,
    program: str | None = None,
) -> DocumentRead:
    """Save to storage, create row with status='pending', dispatch ingest task.

    `program`: carrera a la que aplica el doc (SW-46). Se normaliza al slug
    canónico para que matchee la carrera del alumno en el retrieval. None/vacío
    (= "General") deja el doc visible a todas las carreras.
    """
    sha256 = hashlib.sha256(content).hexdigest()

    existing = await document_repository.get_by_sha256(db, sha256)
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"document already exists (id={existing.id})",
        )

    storage_key = f"docs/{sha256}/{filename}"
    await get_storage().save(storage_key, content)

    doc = Document(
        title=filename,
        program=canonical_program(program),
        source_type=source_type,
        s3_key=storage_key,
        sha256=sha256,
        status=DocumentStatus.pending,
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Lazy import to avoid Celery import side effects during tests
    from chatbot_api.workers.ingest import ingest_document

    ingest_document.delay(doc.id)

    return DocumentRead.model_validate(doc).model_copy(update={"chunk_count": 0})


async def delete_document(db: AsyncSession, document_id: int) -> None:
    doc = await document_repository.get(db, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    await get_storage().delete(doc.s3_key)
    await document_repository.delete(db, document_id)  # cascade delete chunks
    await db.commit()


async def get_public_file(db: AsyncSession, document_id: int) -> tuple[bytes, str]:
    """Devuelve (contenido, título) de un doc para el endpoint público /docs/{id}.

    Solo sirve documentos ya `indexed` (no expone pendientes/errados). El bucket
    sigue privado: esto es un proxy de lectura, no acceso directo al S3.
    """
    doc = await document_repository.get(db, document_id)
    if doc is None or doc.status != DocumentStatus.indexed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    content = await get_storage().get(doc.s3_key)
    return content, doc.title
