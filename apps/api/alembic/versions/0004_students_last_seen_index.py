"""students last_seen index

Revision ID: 0004_students_last_seen
Revises: fa3f45027414
Create Date: 2026-05-06 16:05:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_students_last_seen"
down_revision: str | Sequence[str] | None = "fa3f45027414"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_students_last_seen_at",
        "students",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_students_last_seen_at", table_name="students")
