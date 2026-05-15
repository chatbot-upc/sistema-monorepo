"""seed full intent catalog (SW-14)

Adds the 4 intents missing from the baseline so SBERT + the LLM classifier
prompt agree on the 7 canonical intents.

Revision ID: 0005_seed_intents_full
Revises: 91898e0866cc
Create Date: 2026-05-15 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_seed_intents_full"
down_revision: str | Sequence[str] | None = "91898e0866cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INTENTS = [
    (
        "consulta_mallas",
        "Consultas sobre malla curricular, planes de estudio y cursos por ciclo",
        [
            "qué cursos llevo en el ciclo 5",
            "muéstrame la malla de Ing Industrial",
            "qué prerrequisitos tiene el curso de cálculo",
            "plan de estudios de Administración",
        ],
    ),
    (
        "consulta_reglamento",
        "Consultas sobre normas académicas, reglamento de matrícula y disciplina",
        [
            "cuántas veces puedo desaprobar un curso",
            "qué dice el reglamento sobre asistencia",
            "puedo retirarme de una asignatura",
            "qué pasa si tengo tres jalados",
        ],
    ),
    (
        "solicita_humano",
        "El estudiante pide explícitamente hablar con un asesor humano",
        [
            "quiero hablar con un asesor",
            "necesito una persona, no un bot",
            "pásame con alguien por favor",
            "déjame hablar con un humano",
        ],
    ),
    (
        "otros",
        "Saludos, despedidas, agradecimientos o temas fuera de alcance UPC",
        [
            "hola buenas tardes",
            "gracias por tu ayuda",
            "qué tal estás",
            "hasta luego",
        ],
    ),
]


def upgrade() -> None:
    for name, desc, examples in _INTENTS:
        examples_json = "[" + ", ".join(f'"{e}"' for e in examples) + "]"
        op.execute(
            f"""
            INSERT INTO intents (name, description, examples, active)
            VALUES ('{name}', '{desc.replace("'", "''")}',
                    '{examples_json}'::jsonb, true)
            ON CONFLICT (name) DO NOTHING
            """
        )


def downgrade() -> None:
    names = ", ".join(f"'{name}'" for name, _, _ in _INTENTS)
    op.execute(f"DELETE FROM intents WHERE name IN ({names})")
