from datetime import datetime

from pydantic import BaseModel, ConfigDict

from chatbot_api.models.enums import DocumentSourceType, DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    program: str | None = None
    source_type: DocumentSourceType
    source_url: str | None
    s3_key: str
    sha256: str
    version: int
    status: DocumentStatus
    error_message: str | None
    indexed_at: datetime | None
    created_at: datetime
    chunk_count: int = 0


class DocumentSummary(BaseModel):
    """Aggregate counts across every document for the admin dashboard."""

    total: int
    total_chunks: int
    indexed: int
    indexing: int
    pending: int
    error: int


class ProgramOption(BaseModel):
    """Opción del selector "Programa/carrera" al subir un documento (SW-46).

    `value` es el slug canónico que se guarda en documents.program; `label` es
    la carrera legible. Se derivan de las carreras reales de los estudiantes.
    """

    value: str
    label: str
