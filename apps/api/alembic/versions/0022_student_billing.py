"""student_billing_installments (EP08)

Cuotas de facturación SIMULADAS por número de WhatsApp. Alimentan las consultas
de pagos del bot (SW-49/SW-50/SW-51). Sin integración con el sistema financiero
real; se siembran con scripts/seed_student_billing.py.

Revision ID: 0022_student_billing
Revises: 0021_agent_prompt_v10
Create Date: 2026-07-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_student_billing"
down_revision: str | Sequence[str] | None = "0021_agent_prompt_v10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_billing_installments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("phone_e164", sa.String(length=32), nullable=False),
        sa.Column("cycle", sa.String(length=20), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("concept", sa.String(length=160), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="PEN",
            nullable=False,
        ),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pendiente", "pagado", name="billing_status"),
            server_default="pendiente",
            nullable=False,
        ),
        sa.Column("paid_at", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_student_billing_installments")
        ),
        sa.UniqueConstraint(
            "phone_e164",
            "cycle",
            "number",
            name="uq_student_billing_phone_cycle_number",
        ),
    )
    op.create_index(
        op.f("ix_student_billing_installments_phone_e164"),
        "student_billing_installments",
        ["phone_e164"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_billing_installments_status"),
        "student_billing_installments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_student_billing_installments_status"),
        table_name="student_billing_installments",
    )
    op.drop_index(
        op.f("ix_student_billing_installments_phone_e164"),
        table_name="student_billing_installments",
    )
    op.drop_table("student_billing_installments")
    sa.Enum(name="billing_status").drop(op.get_bind())
