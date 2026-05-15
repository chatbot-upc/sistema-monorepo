from datetime import datetime

from pydantic import BaseModel, ConfigDict

from chatbot_api.models.enums import DocumentSourceType, DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
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
