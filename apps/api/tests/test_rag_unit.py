"""Unit tests for RAG components (no DB, no OpenAI)."""

from langchain_core.documents import Document as LCDocument

from chatbot_api.rag.splitter import get_splitter


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
