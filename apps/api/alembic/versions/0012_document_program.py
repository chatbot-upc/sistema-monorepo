"""documents.program — scope de RAG por carrera (fix SW-46)

Columna nullable que indica a qué carrera/programa aplica un documento (slug
canónico, ver core.programs). NULL = doc general visible a todas las carreras.
El retrieval filtra `program IS NULL OR program = :carrera_alumno` para no
contaminar entre mallas. No destructiva; el backfill puebla las mallas existentes.

Revision ID: 0012_document_program
Revises: 0011_agent_prompt_v2
Create Date: 2026-06-14 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_document_program"
down_revision: str | Sequence[str] | None = "0011_agent_prompt_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("program", sa.String(length=120), nullable=True),
    )
    op.create_index(
        op.f("ix_documents_program"), "documents", ["program"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_program"), table_name="documents")
    op.drop_column("documents", "program")
