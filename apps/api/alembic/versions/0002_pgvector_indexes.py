"""pgvector indexes and partial uniques

Revision ID: 757b97e74844
Revises: 2891c4218398
Create Date: 2026-05-06 15:29:20.285620

"""

from collections.abc import Sequence

from alembic import op

revision: str = "757b97e74844"
down_revision: str | Sequence[str] | None = "2891c4218398"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    op.execute(
        "CREATE INDEX ix_students_display_name_trgm "
        "ON students USING gin (display_name gin_trgm_ops)"
    )

    op.execute(
        "CREATE UNIQUE INDEX uq_prompt_versions_active "
        "ON prompt_versions (name) WHERE active = true"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_prompt_versions_active")
    op.execute("DROP INDEX IF EXISTS ix_students_display_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
