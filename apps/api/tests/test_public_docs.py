"""Endpoint público /docs/{id}/{slug}.pdf + helpers de slug/URL."""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.text import public_doc_url, slugify
from chatbot_api.models import Document
from chatbot_api.models.enums import DocumentStatus


def test_slugify_strips_accents_and_case() -> None:
    assert (
        slugify("INGENIERÍA DE SISTEMAS DE INFORMACIÓN")
        == "ingenieria-de-sistemas-de-informacion"
    )
    assert slugify("Malla 2025 — v2!") == "malla-2025-v2"
    assert slugify("ñoño") == "nono"
    assert slugify("   ") == "doc"  # nada utilizable → fallback


def test_public_doc_url_none_when_no_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    from chatbot_api.core.settings import get_settings

    get_settings.cache_clear()
    assert public_doc_url(12, "Malla SI") is None


def test_public_doc_url_builds_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://remiai.tech/")  # con "/" final
    from chatbot_api.core.settings import get_settings

    get_settings.cache_clear()
    assert public_doc_url(12, "Malla SI") == "https://remiai.tech/docs/12/malla-si.pdf"


@pytest.mark.asyncio
async def test_get_public_pdf_streams_indexed_doc(
    client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /docs/{id}/{slug}.pdf → 200 con el PDF y headers correctos."""
    from chatbot_api.core import storage as storage_mod
    from chatbot_api.core.storage import LocalFileStorage

    monkeypatch.setattr(storage_mod, "_storage", LocalFileStorage(tmp_path))

    doc = Document(
        title="Malla SI",
        source_type="upload",
        s3_key="docs/malla.pdf",
        sha256="a" * 64,
        status=DocumentStatus.indexed,
    )
    db_session.add(doc)
    await db_session.flush()
    await storage_mod.get_storage().save("docs/malla.pdf", b"%PDF-1.7 fake")

    resp = await client.get(f"/docs/{doc.id}/cualquier-slug.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "inline" in resp.headers["content-disposition"]
    assert resp.content == b"%PDF-1.7 fake"


@pytest.mark.asyncio
async def test_get_public_pdf_404_when_not_indexed(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Un doc pendiente no se sirve públicamente."""
    doc = Document(
        title="pending",
        source_type="upload",
        s3_key="docs/x.pdf",
        sha256="b" * 64,
        status=DocumentStatus.pending,
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.get(f"/docs/{doc.id}/x.pdf")
    assert resp.status_code == 404
