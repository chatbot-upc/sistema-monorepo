from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chatbot_api.services.whatsapp_service import shutdown as whatsapp_shutdown

from .db import dispose_engine
from .logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield
    await whatsapp_shutdown()
    await dispose_engine()
