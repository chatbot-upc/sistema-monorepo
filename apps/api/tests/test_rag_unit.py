"""Unit tests for RAG components (no DB, no OpenAI)."""

from langchain_core.documents import Document as LCDocument

from chatbot_api.rag.splitter import get_splitter, split_for_document

_MALLA_TEXT = """MALLA CURRICULAR
ADMINISTRACION Y MARKETING
CREDITOS GENERALES 35
1
▸▸  CICLO 1  20
HU625 Comprension y Produccion de Lenguaje I 4
AM216 Marketing I 3 No tiene requisitos
6
▸▸  CICLO 6  19
AD213 Administracion de Operaciones 3 MA368 Metodos Cuantitativos
AM219 Marketing digital I 3 AM224 Branding
"""


def test_split_for_document_malla_splits_by_cycle() -> None:
    """Una malla se parte por CICLO (1 chunk por ciclo) + preámbulo, con la carrera."""
    docs = split_for_document(
        [LCDocument(page_content=_MALLA_TEXT)], title="Administración y Marketing"
    )
    assert len(docs) == 3  # preámbulo + ciclo 1 + ciclo 6
    assert all("Administración y Marketing" in d.page_content for d in docs)
    c6 = next(d for d in docs if "CICLO 6" in d.page_content)
    assert "Marketing digital I" in c6.page_content
    assert "AM224 Branding" in c6.page_content  # requisito real preservado
    assert "CICLO 1" not in c6.page_content
    assert "Marketing I" not in c6.page_content  # curso de otro ciclo no se cuela


def test_split_for_document_non_malla_uses_recursive() -> None:
    """Un doc sin ciclos usa el splitter normal (varios chunks por tamaño)."""
    text = "Lorem ipsum dolor sit amet. " * 200
    docs = split_for_document([LCDocument(page_content=text)], title="Calendario")
    assert len(docs) >= 4
    assert all(d.metadata.get("section") != "malla" for d in docs)


def test_splitter_chunk_boundaries() -> None:
    """5000-char text con chunk_size=1000 produce ~5 chunks con overlap."""
    splitter = get_splitter()
    text = "Lorem ipsum dolor sit amet. " * 200  # ~5400 chars
    docs = splitter.split_documents([LCDocument(page_content=text)])

    assert 4 <= len(docs) <= 7, f"expected 4-7 chunks, got {len(docs)}"
    for d in docs:
        assert len(d.page_content) <= 1100, f"chunk too big: {len(d.page_content)}"


def test_splitter_respects_separators() -> None:
    """Splitter prefiere romper en \\n\\n antes que mid-sentence."""
    splitter = get_splitter()
    text = "Section one.\n\n" + ("a" * 950) + "\n\nSection two.\n\n" + ("b" * 950)
    docs = splitter.split_documents([LCDocument(page_content=text)])
    contents = [d.page_content for d in docs]
    # Some chunk should contain "Section one." or "Section two." cleanly
    assert any("Section one" in c for c in contents)
    assert any("Section two" in c for c in contents)
