from typing import Annotated
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.db import get_session
from chatbot_api.core.events import publish_event
from chatbot_api.core.settings import get_settings
from chatbot_api.repositories.message import message_repository
from chatbot_api.schemas.whatsapp import WhatsAppWebhookPayload
from chatbot_api.services.whatsapp_webhook_service import (
    extract_messages,
    extract_statuses,
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
    db: AsyncSession = Depends(get_session),
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

    # Acuses de entrega (sent/delivered/read) de NUESTROS salientes. Se procesan
    # inline (un UPDATE rápido) en vez de en Celery para no cargar el worker; y se
    # emite un evento por cada cambio para que el CRM repinte los checks en vivo.
    status_updates = 0
    for st in extract_statuses(payload):
        msg = await message_repository.update_delivery_status(
            db, st.meta_message_id, st.status
        )
        if msg is not None:
            status_updates += 1
            await publish_event(
                "message.status_changed",
                {
                    "message_id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "delivery_status": msg.delivery_status,
                },
            )
    if status_updates:
        await db.commit()

    log.info(
        "whatsapp_event_received",
        queued=queued,
        total_messages_in_payload=len(messages),
        status_updates=status_updates,
        correlation_id=correlation_id,
    )
    return {"status": "received", "queued": queued}
