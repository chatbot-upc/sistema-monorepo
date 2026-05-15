"""messages.intent_used_fallback flag (SW-28)

Lets us compute SBERT-vs-LLM fallback rate directly from messages without
parsing structlog. Nullable: only set on inbound messages that were classified.

Revision ID: 0007_intent_used_fallback
Revises: 0006_enrich_intent_examples
Create Date: 2026-05-15 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_intent_used_fallback"
down_revision: str | Sequence[str] | None = "0006_enrich_intent_examples"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("intent_used_fallback", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "intent_used_fallback")
