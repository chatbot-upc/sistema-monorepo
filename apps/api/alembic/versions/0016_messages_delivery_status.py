"""Acuse de entrega de mensajes salientes: messages.delivery_status.

Refleja los webhooks `statuses` de Meta (sent → delivered → read → failed) para
pintar los checks en el CRM. Null en los mensajes entrantes del estudiante.

Revision ID: 0016_messages_delivery_status
Revises: 0015_agent_prompt_v4
Create Date: 2026-06-15 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_messages_delivery_status"
down_revision: str | Sequence[str] | None = "0015_agent_prompt_v4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("delivery_status", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "delivery_status")
