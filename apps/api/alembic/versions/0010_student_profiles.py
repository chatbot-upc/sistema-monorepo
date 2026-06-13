"""student_profiles (SW-48)

Perfil académico simulado del estudiante, identificado por número de WhatsApp.
Se siembra desde un dataset externo (scripts/seed_student_profiles.py) y se
consulta al recibir un mensaje para personalizar las respuestas del bot.

Revision ID: 0010_student_profiles
Revises: 0009_seed_agent_system_prompt
Create Date: 2026-06-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_student_profiles"
down_revision: str | Sequence[str] | None = "0009_seed_agent_system_prompt"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("phone_e164", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("career", sa.String(length=120), nullable=True),
        sa.Column("cycle", sa.Integer(), nullable=True),
        sa.Column("campus", sa.String(length=80), nullable=True),
        sa.Column("modality", sa.String(length=40), nullable=True),
        sa.Column("academic_status", sa.String(length=40), nullable=True),
        sa.Column("failed_courses", sa.Text(), nullable=True),
        sa.Column("enrollment_turn", sa.DateTime(), nullable=True),
        sa.Column("english_level", sa.Integer(), nullable=True),
        sa.Column("elective_credits", sa.Integer(), nullable=True),
        sa.Column("internship_credits", sa.Integer(), nullable=True),
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
        sa.PrimaryKeyConstraint("phone_e164", name=op.f("pk_student_profiles")),
    )


def downgrade() -> None:
    op.drop_table("student_profiles")
