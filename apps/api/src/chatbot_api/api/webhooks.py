from typing import Annotated, Any

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from chatbot_api.core.settings import get_settings

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
log = structlog.get_logger()


@router.get("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_verify(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> str:
    settings = get_settings()
    if hub_mode != "subscribe" or not settings.meta_verify_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "verify_token not configured")
    if hub_verify_token != settings.meta_verify_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid verify_token")
    if hub_challenge is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing hub.challenge")
    return hub_challenge


@router.post("/whatsapp")
async def whatsapp_event(payload: dict[str, Any]) -> dict[str, str]:
    log.info("whatsapp_event_received", payload_keys=list(payload.keys()))
    return {"status": "received"}
