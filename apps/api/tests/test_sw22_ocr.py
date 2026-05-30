"""SW-22 — hybrid text extraction + OpenAI Vision OCR fallback.

Fixture `scanned_sample.pdf` tiene 2 páginas:
- Página 0: texto digital (362 chars) → debe ir por `source: text`
- Página 1: blank, sin texto digital → debe ir por `source: ocr`

OCR se mockea — los tests NO pegan a OpenAI.

El fixture fue generado one-shot con:
    doc = pymupdf.open(); p = doc.new_page(...); p.insert_text(...); doc.save(...)
Si necesitas regenerarlo, replica esa receta y verifica que pág 1 tenga 0 chars
en `page.get_text("text")`.
"""

from pathlib import Path

import pytest

from chatbot_api.rag.loaders import load_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "scanned_sample.pdf"


@pytest.fixture
def fake_ocr(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Reemplaza el OCR real por uno determinístico y cuenta invocaciones."""
    calls: list[int] = []

    async def _fake(png_bytes: bytes) -> str:
        calls.append(len(png_bytes))
        return "TEXTO RECUPERADO POR OCR"

    from chatbot_api.rag import loaders as loaders_mod

    monkeypatch.setattr(
        loaders_mod.ocr_service, "extract_text_from_image_bytes", _fake
    )
    return calls


async def test_load_pdf_skips_ocr_for_text_page(
    fake_ocr: list[int],
) -> None:
    """La página 0 tiene texto digital → OCR NO debe invocarse para ella."""
    docs = await load_pdf(FIXTURE)
    assert len(docs) == 2
    page_0 = docs[0]
    assert page_0.metadata["page"] == 0
    assert page_0.metadata["source"] == "text"
    assert "REGLAMENTO DE MATR" in page_0.page_content


async def test_load_pdf_invokes_ocr_for_blank_page(
    fake_ocr: list[int],
) -> None:
    """La página 1 no tiene texto → OCR debe invocarse exactamente 1 vez."""
    docs = await load_pdf(FIXTURE)
    assert len(fake_ocr) == 1
    assert fake_ocr[0] > 0  # PNG bytes pasados
    page_1 = docs[1]
    assert page_1.metadata["page"] == 1
    assert page_1.metadata["source"] == "ocr"
    assert page_1.page_content == "TEXTO RECUPERADO POR OCR"


async def test_load_pdf_metadata_shape(fake_ocr: list[int]) -> None:
    """Todos los docs deben tener page/source."""
    docs = await load_pdf(FIXTURE)
    for d in docs:
        assert set(d.metadata.keys()) == {"page", "source"}
        assert d.metadata["source"] in {"text", "ocr"}


async def test_load_pdf_ocr_disabled_skips_blank_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Con `rag_ocr_enabled=False` la pág blank se skipea (no se llama OCR)."""
    from chatbot_api.core import settings as settings_mod

    settings_mod.get_settings.cache_clear()
    monkeypatch.setenv("RAG_OCR_ENABLED", "false")

    calls: list[int] = []

    async def _fake(png_bytes: bytes) -> str:
        calls.append(1)
        return "no debería llamarse"

    from chatbot_api.rag import loaders as loaders_mod

    monkeypatch.setattr(
        loaders_mod.ocr_service, "extract_text_from_image_bytes", _fake
    )

    docs = await load_pdf(FIXTURE)
    assert len(calls) == 0
    # Solo queda la página 0 (la 1 no tiene texto y OCR estaba off)
    assert len(docs) == 1
    assert docs[0].metadata["source"] == "text"

    settings_mod.get_settings.cache_clear()
