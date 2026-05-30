"""messages.admin_id (SW-38)

Track which admin authored each admin-role message. Nullable because student
and bot messages never have one. ON DELETE SET NULL so removing an admin
doesn't cascade-delete their historical messages.

Revision ID: 0008_messages_admin_id
Revises: 0007_intent_used_fallback
Create Date: 2026-05-29 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_messages_admin_id"
down_revision: str | Sequence[str] | None = "0007_intent_used_fallback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("admin_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_admin_id",
        "messages",
        "admins",
        ["admin_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_admin_id", "messages", type_="foreignkey")
    op.drop_column("messages", "admin_id")
