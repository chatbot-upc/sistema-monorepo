from typing import Annotated
from uuid import uuid4

import structlog
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError

from chatbot_api.core.settings import get_settings
from chatbot_api.schemas.whatsapp import WhatsAppWebhookPayload
from chatbot_api.services.whatsapp_webhook_service import (
    extract_messages,
    verify_signature,
)
from chatbot_api.workers.conversation import process_incoming_message

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
async def whatsapp_event(
    request: Request,
    x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> dict[str, object]:
    settings = get_settings()
    raw_body = await request.body()

    if settings.meta_app_secret:
        if not verify_signature(
            raw_body=raw_body,
            signature_header=x_hub_signature_256,
            app_secret=settings.meta_app_secret,
        ):
            log.warning("whatsapp_invalid_signature")
            raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid signature")
    elif settings.env != "local":
        log.error("whatsapp_app_secret_missing", env=settings.env)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "meta_app_secret not configured"
        )

    try:
        payload = WhatsAppWebhookPayload.model_validate_json(raw_body)
    except ValidationError as exc:
        log.warning("whatsapp_invalid_payload", errors=exc.errors())
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid payload") from exc

    messages = extract_messages(payload)
    correlation_id = x_correlation_id or uuid4().hex

    queued = 0
    for parsed in messages:
        process_incoming_message.delay(parsed.model_dump(), correlation_id)
        queued += 1

    log.info(
        "whatsapp_event_received",
        queued=queued,
        total_messages_in_payload=len(messages),
        correlation_id=correlation_id,
    )
    return {"status": "received", "queued": queued}
