"""Alta idempotente del admin del CRM en producción.

El login usa Cognito para la contraseña, pero `get_current_admin` autoriza
buscando el email del JWT en la tabla `admins`. O sea, el usuario debe existir
en AMBOS lados (Cognito + BD), enlazados por email.

Este módulo crea/actualiza esa fila leyendo `ADMIN_EMAIL` / `ADMIN_NAME` del
entorno. Lo corre el servicio `migrate` del docker-compose justo después de
`alembic upgrade head`, así el admin queda listo en cada deploy sin SQL a mano.

No-op si `ADMIN_EMAIL` está vacío (p. ej. en local/dev se usa el stub X-Dev-User).
Vive bajo `src/` (no en apps/api/scripts) para entrar en la imagen Docker.
"""

import asyncio

import structlog
from sqlalchemy import text

from chatbot_api.core.db import get_session_factory
from chatbot_api.core.settings import get_settings

log = structlog.get_logger()


async def bootstrap_admin() -> None:
    settings = get_settings()
    email = settings.admin_email.strip().lower()
    if not email:
        log.info("admin_bootstrap_skipped", reason="ADMIN_EMAIL vacío")
        return

    name = settings.admin_name.strip() or email
    async with get_session_factory()() as session:
        await session.execute(
            text(
                """
                INSERT INTO admins (cognito_sub, email, name, role, active)
                VALUES (NULL, :email, :name, 'admin', true)
                ON CONFLICT (email)
                DO UPDATE SET name = EXCLUDED.name, active = true
                """
            ),
            {"email": email, "name": name},
        )
        await session.commit()
    log.info("admin_bootstrap_done", email=email)


def main() -> None:
    asyncio.run(bootstrap_admin())


if __name__ == "__main__":
    main()
