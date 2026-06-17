"""Celery task: ingest_document(document_id) — full RAG ingest pipeline."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.celery_app import celery_app
from chatbot_api.core.events import publish_event
from chatbot_api.core.settings import get_settings
from chatbot_api.core.storage import get_storage
from chatbot_api.models import Document
from chatbot_api.models.enums import DocumentStatus
from chatbot_api.rag.embeddings import get_embeddings
from chatbot_api.rag.loaders import load_by_extension
from chatbot_api.rag.malla_extractor import (
    build_malla_chunks,
    extract_malla_rows,
    looks_like_malla,
)
from chatbot_api.rag.splitter import split_for_document
from chatbot_api.repositories.document_chunk import document_chunk_repository

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[Any]:
    """Worker corre en proceso separado del API; abre su propio engine."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def _ingest_async(document_id: int) -> None:
    factory = _make_session_factory()
    async with factory() as db:
        doc = await db.get(Document, document_id)
        if doc is None:
            log.error("ingest_doc_not_found", document_id=document_id)
            return

        try:
            doc.status = DocumentStatus.indexing
            await db.commit()
            await publish_event(
                "document.status_changed",
                {"document_id": doc.id, "status": DocumentStatus.indexing.value},
            )

            content = await get_storage().get(doc.s3_key)
            suffix = Path(doc.s3_key).suffix or ".pdf"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            try:
                lc_docs = await load_by_extension(tmp_path)
                # Splitter estructural: mallas → 1 chunk por ciclo (con la carrera
                # como contexto); resto → chunking normal por caracteres.
                # Mallas: extracción a esquema en 1 llamada (lee cualquier layout
                # del PDF) → chunks limpios por ciclo. Si no es malla o la
                # extracción falla, cae al chunking normal por caracteres.
                full_text = "\n".join(d.page_content for d in lc_docs)
                rows = (
                    await extract_malla_rows(full_text, title=doc.title)
                    if looks_like_malla(full_text)
                    else []
                )
                if rows:
                    splits = build_malla_chunks(rows, title=doc.title)
                else:
                    splits = split_for_document(lc_docs, title=doc.title)
                texts = [s.page_content for s in splits]
                ocr_chunks = sum(
                    1 for s in splits if s.metadata.get("source") == "ocr"
                )

                if not texts:
                    doc.status = DocumentStatus.error
                    doc.error_message = "no text extracted"
                    await db.commit()
                    await publish_event(
                        "document.status_changed",
                        {
                            "document_id": doc.id,
                            "status": DocumentStatus.error.value,
                            "error_message": doc.error_message,
                        },
                    )
                    log.warning("ingest_empty", document_id=document_id)
                    return

                vectors = await get_embeddings().aembed_documents(texts)

                chunks_data = [
                    {
                        "chunk_text": s.page_content,
                        "embedding": vec,
                        "meta": s.metadata,
                        "chunk_index": i,
                    }
                    for i, (s, vec) in enumerate(zip(splits, vectors, strict=True))
                ]
                # Idempotente: borra los chunks previos antes de insertar, para que
                # re-ingestar (p. ej. tras cambiar el chunk_size) re-indexe limpio
                # en vez de duplicar.
                await document_chunk_repository.delete_by_document(db, doc.id)
                await document_chunk_repository.bulk_insert(db, doc.id, chunks_data)

                doc.status = DocumentStatus.indexed
                doc.indexed_at = datetime.now()
                await db.commit()
                await publish_event(
                    "document.status_changed",
                    {
                        "document_id": doc.id,
                        "status": DocumentStatus.indexed.value,
                        "indexed_at": doc.indexed_at.isoformat(),
                        "chunk_count": len(splits),
                    },
                )
                log.info(
                    "ingest_completed",
                    document_id=document_id,
                    chunks=len(splits),
                    ocr_chunks=ocr_chunks,
                )
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as exc:
            doc.status = DocumentStatus.error
            doc.error_message = str(exc)[:500]
            await db.commit()
            await publish_event(
                "document.status_changed",
                {
                    "document_id": doc.id,
                    "status": DocumentStatus.error.value,
                    "error_message": doc.error_message,
                },
            )
            log.exception("ingest_failed", document_id=document_id)
            raise


@celery_app.task(name="ingest_document", bind=True, max_retries=2)  # type: ignore[untyped-decorator]
def ingest_document(self: Any, document_id: int) -> None:
    asyncio.run(_ingest_async(document_id))
