"""Celery task: process_incoming_message — persist inbound WhatsApp message.

Scope SW-13 (plumbing only): upsert student + open conversation + insert message with
idempotency on `meta_message_id`. RAG/intent classification arrive in SW-10/SW-14.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.celery_app import celery_app
from chatbot_api.core.settings import get_settings
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[Any]:
    """Worker runs in a separate process: open its own async engine."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def _process_async(parsed_dict: dict[str, Any], correlation_id: str) -> None:
    parsed = ParsedInboundMessage.model_validate(parsed_dict)
    factory = _make_session_factory()
    async with factory() as db:
        try:
            await student_repository.upsert_by_phone(
                db,
                phone_e164=parsed.from_phone,
                display_name=parsed.display_name,
            )
            conv, created = await conversation_repository.get_or_create_open(
                db, parsed.from_phone
            )
            msg = await message_repository.create_inbound(
                db,
                conversation_id=conv.id,
                content=parsed.text,
                meta_message_id=parsed.meta_message_id,
            )
            if msg is None:
                await db.rollback()
                log.info(
                    "inbound_duplicate",
                    correlation_id=correlation_id,
                    meta_message_id=parsed.meta_message_id,
                )
                return
            await db.commit()
            log.info(
                "inbound_persisted",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                message_id=msg.id,
                conversation_created=created,
            )
        except Exception:
            await db.rollback()
            log.exception(
                "inbound_failed",
                correlation_id=correlation_id,
                meta_message_id=parsed.meta_message_id,
            )
            raise


@celery_app.task(  # type: ignore[untyped-decorator]
    name="process_incoming_message",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def process_incoming_message(
    self: Any,
    parsed: dict[str, Any],
    correlation_id: str,
) -> None:
    asyncio.run(_process_async(parsed, correlation_id))
