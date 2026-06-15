"""Cita/reply de mensajes: in_reply_to_id (FK self) + quoted (snapshot JSONB).

Soporta "responder a un mensaje específico" (estilo WhatsApp context/wamid):
- in_reply_to_id: FK canónica al mensaje citado (ON DELETE SET NULL).
- quoted: snapshot congelado {id, role, content, created_at} para pintar el
  preview en el CRM sin queries extra.

Revision ID: 0014_messages_in_reply_to
Revises: 0013_contact_tags_notes
Create Date: 2026-06-14 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_messages_in_reply_to"
down_revision: str | Sequence[str] | None = "0013_agent_prompt_v3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("in_reply_to_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("quoted", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_messages_in_reply_to_id_messages"),
        "messages",
        "messages",
        ["in_reply_to_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_messages_in_reply_to_id"),
        "messages",
        ["in_reply_to_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_in_reply_to_id"), table_name="messages")
    op.drop_constraint(
        op.f("fk_messages_in_reply_to_id_messages"),
        "messages",
        type_="foreignkey",
    )
    op.drop_column("messages", "quoted")
    op.drop_column("messages", "in_reply_to_id")
