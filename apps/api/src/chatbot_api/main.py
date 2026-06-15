from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .api.public import router as public_router
from .api.v1.router import api_v1_router
from .api.webhooks import router as webhooks_router
from .api.ws.conversations import router as ws_router
from .core.db import get_session
from .core.lifespan import lifespan
from .core.settings import get_settings
from .middlewares.correlation import CorrelationMiddleware
from .schemas.common import HealthResponse

settings = get_settings()

app = FastAPI(
    title="Chatbot UPC API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-Id"],
)
app.add_middleware(CorrelationMiddleware)

app.include_router(webhooks_router)
app.include_router(public_router)
app.include_router(api_v1_router)
app.include_router(ws_router)


@app.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_session)) -> HealthResponse:
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
        env=settings.env,
    )
