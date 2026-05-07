"""Standalone seed script for dev/local resets.

Usage:
    uv run python scripts/seed.py
"""

import asyncio

from sqlalchemy import text

from chatbot_api.core.db import get_session_factory


async def seed() -> None:
    async with get_session_factory()() as session:
        await session.execute(
            text(
                """
                INSERT INTO admins (cognito_sub, email, name, role, active)
                VALUES (NULL, 'dev@upc.edu.pe', 'Dev Admin', 'admin', true)
                ON CONFLICT (email) DO NOTHING
                """
            )
        )

        await session.execute(
            text(
                """
                INSERT INTO intents (name, description, examples, active)
                VALUES
                    ('consulta_fechas', 'Consultas sobre fechas de matrícula y pagos',
                     '["¿Cuándo es el último día de matrícula?"]'::jsonb, true),
                    ('consulta_costos', 'Consultas sobre costos de matrícula y aranceles',
                     '["¿Cuánto cuesta la matrícula?"]'::jsonb, true),
                    ('consulta_becas', 'Consultas sobre becas y financiamiento',
                     '["¿Qué becas hay disponibles?"]'::jsonb, true)
                ON CONFLICT (name) DO NOTHING
                """
            )
        )

        await session.commit()
        print("Seed completed.")


if __name__ == "__main__":
    asyncio.run(seed())
