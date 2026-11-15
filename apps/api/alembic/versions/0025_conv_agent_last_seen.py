"""conversations.agent_last_seen_at para el contador de no leídos del CRM.

Las conversaciones existentes se marcan como vistas ahora: si no, todo el
histórico aparecería como no leído al desplegar.
"""

import sqlalchemy as sa
from alembic import op

revision = "0025_conv_agent_last_seen"
down_revision = "0024_whatsapp_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("agent_last_seen_at", sa.DateTime(), nullable=True),
    )
    op.execute("UPDATE conversations SET agent_last_seen_at = now()")


def downgrade() -> None:
    op.drop_column("conversations", "agent_last_seen_at")
