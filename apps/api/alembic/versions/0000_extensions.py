"""extensions

Revision ID: 0000_init_extensions
Revises:
Create Date: 2026-05-06 16:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0000_init_extensions"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    pass
