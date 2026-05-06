"""seed baseline data

Revision ID: fa3f45027414
Revises: 757b97e74844
Create Date: 2026-05-06 15:29:39.903727

"""

from collections.abc import Sequence

from alembic import op

revision: str = "fa3f45027414"
down_revision: str | Sequence[str] | None = "757b97e74844"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO admins (cognito_sub, email, name, role, active)
        VALUES (NULL, 'dev@upc.edu.pe', 'Dev Admin', 'admin', true)
        ON CONFLICT (email) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO intents (name, description, examples, active)
        VALUES
            ('consulta_fechas', 'Consultas sobre fechas de matrícula y pagos',
             '["¿Cuándo es el último día de matrícula?", "¿Hasta cuándo puedo pagar?"]'::jsonb, true),
            ('consulta_costos', 'Consultas sobre costos de matrícula y aranceles',
             '["¿Cuánto cuesta la matrícula?", "¿Cuál es el costo del crédito?"]'::jsonb, true),
            ('consulta_becas', 'Consultas sobre becas y financiamiento',
             '["¿Qué becas hay disponibles?", "¿Cómo aplico a una beca?"]'::jsonb, true)
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM intents WHERE name IN ('consulta_fechas', 'consulta_costos', 'consulta_becas')")
    op.execute("DELETE FROM admins WHERE email = 'dev@upc.edu.pe'")
