"""Celery task: process_incoming_message — full inbound→RAG→outbound flow.

Steps:
1. Upsert student + get/create open conversation.
2. Insert inbound message (idempotent on meta_message_id).
3. If conversation is in takeover → done (admin will reply manually).
4. Invoke RAG agent.
5. Persist bot message with tokens/latency/retrieved_chunks/meta_message_id.
6. Send via WhatsApp Cloud API.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.celery_app import celery_app
from chatbot_api.core.settings import get_settings
from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.services import rag_service, whatsapp_service

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[Any]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def _process_async(parsed_dict: dict[str, Any], correlation_id: str) -> None:
    parsed = ParsedInboundMessage.model_validate(parsed_dict)
    settings = get_settings()
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
            inbound = await message_repository.create_inbound(
                db,
                conversation_id=conv.id,
                content=parsed.text,
                meta_message_id=parsed.meta_message_id,
            )
            if inbound is None:
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
                message_id=inbound.id,
                conversation_created=created,
            )

            if conv.status == ConversationStatus.takeover:
                log.info(
                    "skip_bot_takeover",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                )
                return

            started = time.perf_counter()
            result = await rag_service.answer(
                user_text=parsed.text, correlation_id=correlation_id
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            answer_text = str(result.get("text") or "")
            if not answer_text:
                log.warning(
                    "rag_empty_answer",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                )
                return

            meta_out_id = await whatsapp_service.send_message(
                to=parsed.from_phone, body=answer_text
            )

            bot_msg = await message_repository.create_bot(
                db,
                conversation_id=conv.id,
                content=answer_text,
                retrieved_chunks=result.get("tool_calls") or [],
                input_tokens=result.get("input_tokens"),
                output_tokens=result.get("output_tokens"),
                latency_ms=latency_ms,
                model_used=settings.openai_model,
                meta_message_id=meta_out_id,
            )
            await db.commit()
            log.info(
                "bot_replied",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                bot_message_id=bot_msg.id,
                latency_ms=latency_ms,
                meta_message_id=meta_out_id,
            )
        except Exception:
            await db.rollback()
            log.exception(
                "process_failed",
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
