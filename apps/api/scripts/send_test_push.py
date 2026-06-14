"""Manual smoke test for SW-33: dispara un push web al admin id=1.

Uso (desde apps/api/):
    uv run python scripts/send_test_push.py

Requiere:
- BD up (docker compose up -d postgres)
- FIREBASE_* configurado en .env
- Al menos un admin_device registrado para admin_id=1
- Browser abierto (en cualquier tab de localhost:3001) para recibir el push
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.services import push_service


async def main(admin_id: int = 1) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        sent = await push_service.notify_admin(
            db,
            admin_id=admin_id,
            title="UPCBot — escalado nuevo",
            body="Un estudiante necesita atencion humana. Toca para abrir.",
            data={"url": "/conversations", "type": "escalation"},
        )
        print(f"sent={sent} push(es) to admin_id={admin_id}")

    await engine.dispose()


if __name__ == "__main__":
    admin_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(main(admin_id))
