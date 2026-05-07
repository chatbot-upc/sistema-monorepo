"""Document loaders. Wrappers thin sobre langchain-community."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, UnstructuredHTMLLoader
from langchain_core.documents import Document as LCDocument


def load_pdf(path: Path) -> list[LCDocument]:
    return PyPDFLoader(str(path)).load()


def load_html(path: Path) -> list[LCDocument]:
    return UnstructuredHTMLLoader(str(path)).load()


def load_by_extension(path: Path) -> list[LCDocument]:
    """Dispatch por extensión."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".html", ".htm"}:
        return load_html(path)
    raise ValueError(f"unsupported extension: {suffix}")
