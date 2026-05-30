import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatbot_api.api.ws.conversations import _redis_subscriber_loop
from chatbot_api.services.whatsapp_service import shutdown as whatsapp_shutdown

from .db import dispose_engine
from .logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    # Bridge Redis pub/sub → connected WS clients (SW-36/37 realtime).
    subscriber_task = asyncio.create_task(_redis_subscriber_loop())
    try:
        yield
    finally:
        subscriber_task.cancel()
        try:
            await subscriber_task
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: S110
            pass
        await whatsapp_shutdown()
        await dispose_engine()
