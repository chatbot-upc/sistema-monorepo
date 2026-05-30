"""Document loaders.

PDF: PyMuPDF (fitz) extrae texto digital por página. Si una página tiene <
`rag_ocr_threshold` chars, la rendereamos a PNG y la pasamos por OpenAI Vision
(SW-22). Esto cubre los PDFs escaneados sin instalar Tesseract en el host.

HTML: wrapper thin sobre langchain-community.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf
import structlog
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_core.documents import Document as LCDocument

from chatbot_api.core.settings import get_settings
from chatbot_api.services import ocr_service

log = structlog.get_logger()


async def load_pdf(path: Path) -> list[LCDocument]:
    """Extract text page-by-page with OCR fallback for scanned pages.

    Cada página produce un LCDocument con metadata:
      - page: índice (0-based)
      - source: "text" si vino del texto digital, "ocr" si fue Vision
      - document_path: ruta del archivo origen
    """
    settings = get_settings()
    docs: list[LCDocument] = []
    ocr_pages = 0
    with pymupdf.open(path) as pdf:  # type: ignore[no-untyped-call]
        for page_idx, page in enumerate(pdf):
            text = page.get_text("text").strip()
            source = "text"
            if (
                len(text) < settings.rag_ocr_threshold
                and settings.rag_ocr_enabled
            ):
                pix = page.get_pixmap(dpi=settings.rag_ocr_dpi)
                png_bytes = pix.tobytes("png")
                text = (
                    await ocr_service.extract_text_from_image_bytes(png_bytes)
                ).strip()
                source = "ocr"
                ocr_pages += 1
            if not text:
                continue
            docs.append(
                LCDocument(
                    page_content=text,
                    metadata={"page": page_idx, "source": source},
                )
            )
    log.info(
        "pdf_loaded",
        path=str(path),
        total_pages=len(docs),
        ocr_pages=ocr_pages,
    )
    return docs


def load_html(path: Path) -> list[LCDocument]:
    return UnstructuredHTMLLoader(str(path)).load()


async def load_by_extension(path: Path) -> list[LCDocument]:
    """Dispatch por extensión."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return await load_pdf(path)
    if suffix in {".html", ".htm"}:
        return load_html(path)
    raise ValueError(f"unsupported extension: {suffix}")
