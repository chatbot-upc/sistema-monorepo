from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdPk, Timestamped
from .enums import DocumentSourceType, DocumentStatus

if TYPE_CHECKING:
    from .document_chunk import DocumentChunk


class Document(IdPk, Timestamped, Base):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    # Carrera/programa al que aplica el doc (slug canónico, ver core.programs).
    # NULL = doc general (fechas, becas, reglamentos) → visible a todas las
    # carreras. Si tiene valor, el retrieval lo restringe a alumnos de esa
    # carrera. Lo setea el upload (panel) o el backfill de mallas.
    program: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True
    )
    source_type: Mapped[DocumentSourceType] = mapped_column(
        Enum(DocumentSourceType, name="document_source_type"),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    version_history: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.pending,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    indexed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
