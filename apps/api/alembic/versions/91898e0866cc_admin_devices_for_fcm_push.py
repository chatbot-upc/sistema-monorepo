"""admin_devices for fcm push

Revision ID: 91898e0866cc
Revises: 0004_students_last_seen
Create Date: 2026-05-08 17:30:05.591739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '91898e0866cc'
down_revision: Union[str, Sequence[str], None] = '0004_students_last_seen'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'admin_devices',
        sa.Column('admin_id', sa.BigInteger(), nullable=False),
        sa.Column('fcm_token', sa.String(length=2048), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['admin_id'], ['admins.id'],
            name=op.f('fk_admin_devices_admin_id_admins'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_admin_devices')),
        sa.UniqueConstraint('fcm_token', name='uq_admin_devices_fcm_token'),
    )
    op.create_index(
        op.f('ix_admin_devices_admin_id'),
        'admin_devices',
        ['admin_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_admin_devices_admin_id'), table_name='admin_devices')
    op.drop_table('admin_devices')
