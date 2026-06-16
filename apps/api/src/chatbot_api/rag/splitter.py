"""Chunking de documentos.

- Mallas (tablas por ciclo): splitter ESTRUCTURAL → 1 chunk por CICLO. Partir una
  malla por caracteres mezcla los ciclos y el LLM alucina; partir por la sección
  natural ("▸▸ CICLO N") da chunks limpios, embeddings precisos por ciclo y los
  requisitos de cada curso intactos.
- Resto de documentos: RecursiveCharacterTextSplitter (chunk_size configurable).
"""

import re

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from chatbot_api.core.settings import get_settings

# Encabezado de ciclo en el texto extraído de la malla, p. ej. "6\n▸▸  CICLO 6".
# Tolerante al marcador (▸/►/>) y a espacios/saltos.
_CYCLE_RE = re.compile(r"(?im)^[^\S\n]*\d+[\s▸►>]*CICLO\s+\d+\b")
_MIN_CYCLES = 2  # con <2 no parece una malla → splitter normal


def get_splitter() -> RecursiveCharacterTextSplitter:
    s = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=s.rag_chunk_size,
        chunk_overlap=s.rag_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_for_document(
    lc_docs: list[LCDocument], title: str | None = None
) -> list[LCDocument]:
    """Devuelve los chunks de un documento.

    Si el texto tiene varios encabezados "CICLO N" (es una malla), parte por
    ciclo y antepone el nombre de la carrera (`title`) a cada chunk para que el
    embedding y el LLM sepan a qué carrera pertenece. Si no, usa el splitter
    normal por caracteres.
    """
    full = "\n".join(d.page_content for d in lc_docs)
    starts = [m.start() for m in _CYCLE_RE.finditer(full)]
    if len(starts) < _MIN_CYCLES:
        return get_splitter().split_documents(lc_docs)

    base_meta = dict(lc_docs[0].metadata) if lc_docs else {}
    prefix = f"{title}\n" if title else ""
    bounds = [0, *starts, len(full)]  # incluye el preámbulo (créditos generales…)
    chunks: list[LCDocument] = []
    for i in range(len(bounds) - 1):
        section = full[bounds[i] : bounds[i + 1]].strip()
        if not section:
            continue
        chunks.append(
            LCDocument(
                page_content=f"{prefix}{section}",
                metadata={**base_meta, "section": "malla"},
            )
        )
    return chunks
