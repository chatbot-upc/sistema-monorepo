from fastapi import FastAPI

from .core.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Chatbot UPC API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env}
