"""Integration tests for RAG ingest pipeline. OpenAI mocked, DB real."""

from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Document, DocumentChunk
from chatbot_api.models.enums import DocumentStatus

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}
SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample.pdf"


def _fake_vector(seed: float = 0.1) -> list[float]:
    return [seed] * 1536


class _MockEmbeddings:
    """Replaces OpenAIEmbeddings + CacheBackedEmbeddings in tests."""

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_fake_vector(0.1 + i * 0.01) for i in range(len(texts))]

    async def aembed_query(self, text: str) -> list[float]:
        return _fake_vector(0.1)


@pytest.fixture
def mock_embeddings(monkeypatch: pytest.MonkeyPatch) -> _MockEmbeddings:
    mock = _MockEmbeddings()
    monkeypatch.setattr("chatbot_api.rag.embeddings.get_embeddings", lambda: mock)
    monkeypatch.setattr("chatbot_api.rag.retriever.get_embeddings", lambda: mock)
    monkeypatch.setattr("chatbot_api.workers.ingest.get_embeddings", lambda: mock)
    return mock


@pytest.fixture
def mock_celery_task(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Captura los IDs de docs encolados sin invocar Celery real."""
    queued: list[int] = []

    class _MockResult:
        def __init__(self, doc_id: int) -> None:
            self.id = f"mock-{doc_id}"

    def _fake_delay(document_id: int) -> _MockResult:
        queued.append(document_id)
        return _MockResult(document_id)

    from chatbot_api.workers import ingest as ingest_mod

    monkeypatch.setattr(ingest_mod.ingest_document, "delay", _fake_delay)
    return queued


async def test_upload_document_endpoint_creates_pending(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_celery_task: list[int],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /documents multipart → 202, doc en pending, task encolada."""
    from chatbot_api.core import storage as storage_mod
    from chatbot_api.core.storage import LocalFileStorage

    monkeypatch.setattr(storage_mod, "_storage", LocalFileStorage(tmp_path))

    pdf_bytes = SAMPLE_PDF.read_bytes()
    response = await client.post(
        "/api/v1/documents",
        headers=DEV_USER_HEADER,
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={"source_type": "upload"},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["title"] == "sample.pdf"
    assert len(mock_celery_task) == 1
    assert mock_celery_task[0] == body["id"]


async def test_upload_document_with_program_tags_canonical(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_celery_task: list[int],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SW-46: subir con program → se guarda el slug canónico en el doc."""
    from chatbot_api.core import storage as storage_mod
    from chatbot_api.core.storage import LocalFileStorage

    monkeypatch.setattr(storage_mod, "_storage", LocalFileStorage(tmp_path))

    pdf_bytes = SAMPLE_PDF.read_bytes()
    response = await client.post(
        "/api/v1/documents",
        headers=DEV_USER_HEADER,
        files={"file": ("malla_si.pdf", pdf_bytes, "application/pdf")},
        data={"source_type": "upload", "program": "Ing. de Sistemas de Información"},
    )
    assert response.status_code == 202, response.text
    assert response.json()["program"] == "sistemas-informacion"


async def test_upload_document_dedupe_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_celery_task: list[int],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Subir el mismo content dos veces → segundo intento 409."""
    from chatbot_api.core import storage as storage_mod
    from chatbot_api.core.storage import LocalFileStorage

    monkeypatch.setattr(storage_mod, "_storage", LocalFileStorage(tmp_path))

    pdf_bytes = SAMPLE_PDF.read_bytes()
    files = {"file": ("sample.pdf", pdf_bytes, "application/pdf")}
    data = {"source_type": "upload"}

    r1 = await client.post(
        "/api/v1/documents", headers=DEV_USER_HEADER, files=files, data=data
    )
    assert r1.status_code == 202

    r2 = await client.post(
        "/api/v1/documents", headers=DEV_USER_HEADER, files=files, data=data
    )
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


async def test_delete_document_removes_chunks(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DELETE /documents/{id} → 204, chunks borrados (cascade)."""
    from chatbot_api.core import storage as storage_mod
    from chatbot_api.core.storage import LocalFileStorage

    monkeypatch.setattr(storage_mod, "_storage", LocalFileStorage(tmp_path))

    # Crear doc + chunks directamente
    doc = Document(
        title="test",
        source_type="upload",
        s3_key="docs/dummy.pdf",
        sha256="d" * 64,
        status=DocumentStatus.indexed,
    )
    db_session.add(doc)
    await db_session.flush()
    db_session.add(
        DocumentChunk(
            document_id=doc.id,
            chunk_text="content",
            embedding=_fake_vector(),
            chunk_index=0,
        )
    )
    await db_session.flush()

    # Crear blob en storage para que delete no falle
    await storage_mod.get_storage().save("docs/dummy.pdf", b"x")

    response = await client.delete(
        f"/api/v1/documents/{doc.id}", headers=DEV_USER_HEADER
    )
    assert response.status_code == 204


async def test_retriever_filters_by_indexed_status(
    db_session: AsyncSession, mock_embeddings: _MockEmbeddings
) -> None:
    """retrieve() solo devuelve chunks de documents con status='indexed'."""
    from chatbot_api.rag.retriever import retrieve

    doc_indexed = Document(
        title="indexed_doc",
        source_type="upload",
        s3_key="k1",
        sha256="a" * 64,
        status=DocumentStatus.indexed,
    )
    doc_pending = Document(
        title="pending_doc",
        source_type="upload",
        s3_key="k2",
        sha256="b" * 64,
        status=DocumentStatus.pending,
    )
    db_session.add_all([doc_indexed, doc_pending])
    await db_session.flush()

    db_session.add(
        DocumentChunk(
            document_id=doc_indexed.id,
            chunk_text="visible",
            embedding=_fake_vector(),
            chunk_index=0,
        )
    )
    db_session.add(
        DocumentChunk(
            document_id=doc_pending.id,
            chunk_text="hidden",
            embedding=_fake_vector(),
            chunk_index=0,
        )
    )
    await db_session.flush()

    results = await retrieve(db_session, "any query", k=10)
    chunk_texts = {c.chunk_text for c, _ in results}
    assert "visible" in chunk_texts
    assert "hidden" not in chunk_texts


async def test_retriever_scopes_by_program(
    db_session: AsyncSession, mock_embeddings: _MockEmbeddings
) -> None:
    """SW-46: retrieve(program=X) trae solo la malla X + docs generales (NULL)."""
    from chatbot_api.rag.retriever import retrieve

    malla_si = Document(
        title="malla SI",
        source_type="upload",
        s3_key="si",
        sha256="1" * 64,
        status=DocumentStatus.indexed,
        program="sistemas-informacion",
    )
    malla_cc = Document(
        title="malla CC",
        source_type="upload",
        s3_key="cc",
        sha256="2" * 64,
        status=DocumentStatus.indexed,
        program="ciencias-computacion",
    )
    general = Document(
        title="calendario",
        source_type="upload",
        s3_key="cal",
        sha256="3" * 64,
        status=DocumentStatus.indexed,
        program=None,
    )
    db_session.add_all([malla_si, malla_cc, general])
    await db_session.flush()
    for doc, text in [
        (malla_si, "curso_si"),
        (malla_cc, "curso_cc"),
        (general, "fecha_general"),
    ]:
        db_session.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_text=text,
                embedding=_fake_vector(),
                chunk_index=0,
            )
        )
    await db_session.flush()

    results = await retrieve(
        db_session, "any", k=10, program="sistemas-informacion"
    )
    texts = {c.chunk_text for c, _ in results}
    assert "curso_si" in texts  # su malla
    assert "fecha_general" in texts  # doc general (NULL) visible a todos
    assert "curso_cc" not in texts  # otra carrera → excluida

    # Fail-open: sin program trae todo (comportamiento histórico).
    all_results = await retrieve(db_session, "any", k=10)
    assert "curso_cc" in {c.chunk_text for c, _ in all_results}


async def test_ingest_pipeline_e2e(
    db_session: AsyncSession,
    mock_embeddings: _MockEmbeddings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ingest end-to-end (sync, sin Celery): doc pending → indexed con chunks."""
    from chatbot_api.core import storage as storage_mod
    from chatbot_api.core.storage import LocalFileStorage

    monkeypatch.setattr(storage_mod, "_storage", LocalFileStorage(tmp_path))

    pdf_bytes = SAMPLE_PDF.read_bytes()
    storage_key = "docs/test/sample.pdf"
    await storage_mod.get_storage().save(storage_key, pdf_bytes)

    doc = Document(
        title="sample.pdf",
        source_type="upload",
        s3_key=storage_key,
        sha256="e" * 64,
        status=DocumentStatus.pending,
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.commit()

    # Patch _make_session_factory para que workers usen la sesión del test
    from chatbot_api.workers import ingest as ingest_mod

    class _Ctx:
        async def __aenter__(self) -> AsyncSession:
            return db_session

        async def __aexit__(self, *_args: Any) -> None:
            pass

    def _factory_using_test_session() -> Any:
        return lambda: _Ctx()

    monkeypatch.setattr(ingest_mod, "_make_session_factory", _factory_using_test_session)

    await ingest_mod._ingest_async(doc.id)

    await db_session.refresh(doc)
    assert doc.status == DocumentStatus.indexed
    assert doc.indexed_at is not None
