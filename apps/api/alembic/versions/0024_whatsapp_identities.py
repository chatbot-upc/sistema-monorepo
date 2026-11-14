"""Stable contact IDs and scoped WhatsApp aliases.

Phone columns are academic identifiers, never opaque WhatsApp routing IDs.
"""

from alembic import op
import sqlalchemy as sa

revision = "0024_whatsapp_identities"
down_revision = "0023_seed_intent_consulta_pagos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BIGSERIAL assigns every existing contact an ID before the FK is populated.
    op.execute("ALTER TABLE students ADD COLUMN id BIGSERIAL NOT NULL")
    op.add_column("conversations", sa.Column("student_id", sa.BigInteger(), nullable=True))
    op.execute(
        "UPDATE conversations c SET student_id=s.id FROM students s WHERE s.phone_e164=c.student_phone"
    )
    op.drop_constraint(
        "fk_conversations_student_phone_students", "conversations", type_="foreignkey"
    )
    op.drop_constraint("pk_students", "students", type_="primary")
    op.create_primary_key("pk_students", "students", ["id"])
    op.create_unique_constraint("uq_students_phone_e164", "students", ["phone_e164"])
    op.alter_column("students", "phone_e164", nullable=True)
    op.alter_column("conversations", "student_phone", nullable=True)
    op.alter_column("conversations", "student_id", nullable=False)
    op.create_foreign_key(
        "fk_conversations_student_id_students",
        "conversations",
        "students",
        ["student_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_conversations_student_id", "conversations", ["student_id"])
    for name, length in [
        ("whatsapp_user_id", 160),
        ("whatsapp_username", 255),
        ("whatsapp_scope", 255),
        ("business_phone_number_id", 160),
        ("whatsapp_routing_id", 160),
    ]:
        op.add_column("students", sa.Column(name, sa.String(length), nullable=True))
    op.add_column(
        "students",
        sa.Column("identity_timestamp", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "students",
        sa.Column("phone_timestamp", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_table(
        "whatsapp_identities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(160), nullable=False),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("students.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("business_phone_number_id", sa.String(160)),
        sa.Column("parent_user_id", sa.String(160)),
        sa.Column("username", sa.String(255)),
        sa.UniqueConstraint("scope", "user_id"),
    )
    op.create_index("ix_whatsapp_identities_student_id", "whatsapp_identities", ["student_id"])
    op.create_table(
        "whatsapp_identity_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("meta_message_id", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("scope", "meta_message_id"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Refuse loss of aliases, replay protection, or contacts without phones.
    unsafe = bind.execute(
        sa.text("""SELECT EXISTS(SELECT 1 FROM students WHERE phone_e164 IS NULL OR whatsapp_user_id IS NOT NULL OR whatsapp_routing_id IS NOT NULL)
        OR EXISTS(SELECT 1 FROM whatsapp_identities) OR EXISTS(SELECT 1 FROM whatsapp_identity_events)
        OR EXISTS(SELECT 1 FROM conversations c JOIN students s ON s.id=c.student_id WHERE c.student_phone IS DISTINCT FROM s.phone_e164)""")
    ).scalar()
    if unsafe:
        raise RuntimeError(
            "Cannot downgrade WhatsApp identity data losslessly; retain 0024 or restore a verified pre-migration backup"
        )
    op.drop_table("whatsapp_identity_events")
    op.drop_table("whatsapp_identities")
    op.drop_constraint("fk_conversations_student_id_students", "conversations", type_="foreignkey")
    op.drop_column("conversations", "student_id")
    for name in [
        "whatsapp_user_id",
        "whatsapp_username",
        "whatsapp_scope",
        "business_phone_number_id",
        "whatsapp_routing_id",
        "identity_timestamp",
        "phone_timestamp",
    ]:
        op.drop_column("students", name)
    op.drop_constraint("pk_students", "students", type_="primary")
    op.drop_constraint("uq_students_phone_e164", "students", type_="unique")
    op.alter_column("students", "phone_e164", nullable=False)
    op.create_primary_key("pk_students", "students", ["phone_e164"])
    op.drop_column("students", "id")
    op.alter_column("conversations", "student_phone", nullable=False)
    op.create_foreign_key(
        "fk_conversations_student_phone_students",
        "conversations",
        "students",
        ["student_phone"],
        ["phone_e164"],
        ondelete="RESTRICT",
    )
