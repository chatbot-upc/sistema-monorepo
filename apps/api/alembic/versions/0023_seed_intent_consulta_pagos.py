"""seed intent consulta_pagos (EP08 / SW-51)

Nuevo intent para consultas PERSONALES de pagos/deuda del estudiante (su estado
de cuenta), distinto de `consulta_costos` (aranceles institucionales genéricos,
resueltos vía RAG). Los `examples` alimentan el índice SBERT del clasificador;
usan lenguaje posesivo ("mi deuda", "tengo pendiente") para separarse de las
consultas genéricas de costos.

NOTA: el worker cachea el índice de intents en memoria y lo invalida vía la
generación en Redis (`bump_index_generation`, disparada por el CRUD de intents).
Un seed por migración no la incrementa, así que el worker toma el nuevo intent
en su próximo arranque (o al reconstruir el índice). En deploy normal esto ocurre
solo; en dev, reinicia el worker.

Revision ID: 0023_seed_intent_consulta_pagos
Revises: 0022_student_billing
Create Date: 2026-07-03 12:05:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023_seed_intent_consulta_pagos"
down_revision: str | Sequence[str] | None = "0022_student_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO intents (name, description, examples, active)
        VALUES (
            'consulta_pagos',
            'Consultas personales sobre el estado de pagos, deuda y cuotas del propio estudiante',
            '[
                "¿Tengo pagos pendientes este ciclo?",
                "¿Cuánto debo?",
                "¿Cuánto me falta pagar?",
                "¿Cuál es mi deuda actual?",
                "¿Cuándo vence mi próxima cuota?",
                "¿De cuánto es mi próxima cuota?",
                "Quiero ver mi estado de cuenta",
                "¿Ya pagué mi matrícula?",
                "¿Me falta alguna cuota por pagar?",
                "¿Tengo alguna cuota vencida?",
                "¿Cuánto tengo que pagar y hasta cuándo?",
                "Mis pagos pendientes"
            ]'::jsonb,
            true
        )
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM intents WHERE name = 'consulta_pagos'")
