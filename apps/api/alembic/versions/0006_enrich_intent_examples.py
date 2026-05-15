"""enrich examples on the 3 baseline intents (SW-14)

The baseline seed (0003) shipped each intent with only 2 examples — not enough
signal for SBERT to disambiguate against the 4 intents added in 0005. This
revision REPLACES the example arrays for the 3 originals with richer sets that
match the diversity of the new ones.

Revision ID: 0006_enrich_intent_examples
Revises: 0005_seed_intents_full
Create Date: 2026-05-15 12:30:00.000000

"""

import json
from collections.abc import Sequence

from alembic import op
from sqlalchemy import bindparam, text

revision: str = "0006_enrich_intent_examples"
down_revision: str | Sequence[str] | None = "0005_seed_intents_full"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ENRICHED: list[tuple[str, list[str]]] = [
    (
        "consulta_fechas",
        [
            "¿Cuándo es el último día de matrícula?",
            "hasta cuando puedo matricularme este ciclo",
            "fecha límite de matrícula",
            "cuándo cierra la matrícula",
            "¿Hasta cuándo puedo pagar?",
            "plazo para pagar la primera cuota",
            "calendario académico 2025-2",
            "cuándo es el examen final",
        ],
    ),
    (
        "consulta_costos",
        [
            "¿Cuánto cuesta la matrícula?",
            "¿Cuál es el costo del crédito?",
            "cuanto sale la cuota",
            "precio del semestre",
            "cuánto tengo que pagar",
            "monto de la pensión",
            "tarifa por crédito",
            "cobro por mora",
        ],
    ),
    (
        "consulta_becas",
        [
            "¿Qué becas hay disponibles?",
            "¿Cómo aplico a una beca?",
            "perdí mi beca, qué hago",
            "requisitos para la beca 18",
            "crédito educativo UPC",
            "puedo renovar mi beca",
            "financiamiento para mis estudios",
            "ayuda económica para alumnos",
        ],
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    for name, examples in _ENRICHED:
        conn.execute(
            text(
                "UPDATE intents SET examples = CAST(:examples AS jsonb) "
                "WHERE name = :name"
            ).bindparams(
                bindparam("examples", value=json.dumps(examples)),
                bindparam("name", value=name),
            )
        )


def downgrade() -> None:
    pass
