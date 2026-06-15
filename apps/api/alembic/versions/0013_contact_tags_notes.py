"""Ficha de contacto: email, destacar, etiquetas y notas internas.

- students.email: correo editable del estudiante (nullable).
- conversations.starred: marca de conversación destacada.
- tags + conversation_tags: catálogo global de etiquetas y su asignación N:N.
- internal_notes: notas internas del asesor por conversación (CRUD).

Revision ID: 0013_contact_tags_notes
Revises: 0012_document_program
Create Date: 2026-06-14 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_contact_tags_notes"
down_revision: str | Sequence[str] | None = "0012_document_program"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # students.email
    op.add_column(
        "students",
        sa.Column("email", sa.String(length=255), nullable=True),
    )

    # conversations.starred
    op.add_column(
        "conversations",
        sa.Column(
            "starred",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # tags (catálogo global)
    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("name", name=op.f("uq_tags_name")),
    )

    # conversation_tags (puente N:N)
    op.create_table(
        "conversation_tags",
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_conversation_tags_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_conversation_tags_tag_id_tags"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id", "tag_id", name=op.f("pk_conversation_tags")
        ),
    )

    # internal_notes (notas por conversación)
    op.create_table(
        "internal_notes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("author_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_internal_notes_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_admin_id"],
            ["admins.id"],
            name=op.f("fk_internal_notes_author_admin_id_admins"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_internal_notes")),
    )
    op.create_index(
        op.f("ix_internal_notes_conversation_id"),
        "internal_notes",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_internal_notes_conversation_id"), table_name="internal_notes"
    )
    op.drop_table("internal_notes")
    op.drop_table("conversation_tags")
    op.drop_table("tags")
    op.drop_column("conversations", "starred")
    op.drop_column("students", "email")
