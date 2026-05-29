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
import gc
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.celery_app import celery_app
from chatbot_api.core.settings import get_settings
from chatbot_api.models import ConversationIntent, Message
from chatbot_api.models.enums import ConversationStatus, MessageRole
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.services import intent_classifier_service, rag_service, whatsapp_service

log = structlog.get_logger()

_WELCOME_PATH = (
    Path(__file__).parent.parent / "prompts" / "v1" / "welcome.md"
)
_welcome_text: str | None = None


def _get_welcome_text() -> str:
    global _welcome_text
    if _welcome_text is None:
        _welcome_text = _WELCOME_PATH.read_text(encoding="utf-8").strip()
    return _welcome_text


def _make_session_factory() -> async_sessionmaker[Any]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


_HISTORY_WINDOW_HOURS = 24
_HISTORY_LIMIT = 20


def _to_chat_history(messages: list[Message]) -> list[dict[str, str]]:
    """Map DB messages to LangChain chat format. Skip empty content.

    student → user · bot/admin → assistant (admin handles takeover continuity).
    """
    history: list[dict[str, str]] = []
    for m in messages:
        if not m.content:
            continue
        role = "user" if m.role == MessageRole.student else "assistant"
        history.append({"role": role, "content": m.content})
    return history


async def _process_async(parsed_dict: dict[str, Any], correlation_id: str) -> None:
    parsed = ParsedInboundMessage.model_validate(parsed_dict)
    settings = get_settings()
    factory = _make_session_factory()

    async with factory() as db:
        try:
            _, student_created = await student_repository.upsert_by_phone(
                db,
                phone_e164=parsed.from_phone,
                display_name=parsed.display_name,
            )
            conv, conv_created = await conversation_repository.get_or_create_open(
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
                conversation_created=conv_created,
                student_created=student_created,
            )

            intent_result = await intent_classifier_service.classify(
                db=db, text=parsed.text
            )
            inbound.intent_used_fallback = bool(intent_result["used_fallback"])
            if intent_result["intent_id"] is not None:
                inbound.intent_id = intent_result["intent_id"]
                db.add(
                    ConversationIntent(
                        conversation_id=conv.id,
                        intent_id=intent_result["intent_id"],
                        confidence=float(intent_result["confidence"]),
                    )
                )
            await db.commit()
            log.info(
                "intent_classified",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                message_id=inbound.id,
                intent_name=intent_result["intent_name"],
                confidence=intent_result["confidence"],
                used_fallback=intent_result["used_fallback"],
                sbert_intent_name=intent_result["sbert_intent_name"],
                sbert_confidence=intent_result["sbert_confidence"],
            )

            if conv.status == ConversationStatus.takeover:
                log.info(
                    "skip_bot_takeover",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                )
                return

            # SW-30: deterministic escalation when the classifier resolves the
            # message to "solicita_humano" (e.g. "quiero hablar con un asesor").
            # Skip the RAG roundtrip entirely — the LLM doesn't need to decide.
            # The student-facing notice + admin push belong to SW-29/SW-31.
            if intent_result.get("intent_name") == "solicita_humano":
                conv.status = ConversationStatus.takeover
                conv.meta = {
                    **(conv.meta or {}),
                    "escalation_reason": "intent:solicita_humano",
                    "escalation_source": "intent_classifier",
                    "escalated_at": datetime.now().isoformat(),
                    "escalated_from_message_id": inbound.id,
                }
                await db.commit()
                log.info(
                    "conversation_escalated",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                    reason="intent:solicita_humano",
                    source="intent_classifier",
                )
                return

            if student_created:
                welcome_text = _get_welcome_text()
                welcome_meta_id = await whatsapp_service.send_message(
                    to=parsed.from_phone, body=welcome_text
                )
                welcome_msg = await message_repository.create_bot(
                    db,
                    conversation_id=conv.id,
                    content=welcome_text,
                    meta_message_id=welcome_meta_id,
                )
                await db.commit()
                log.info(
                    "welcome_sent",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                    bot_message_id=welcome_msg.id,
                    meta_message_id=welcome_meta_id,
                )

            since = datetime.now() - timedelta(hours=_HISTORY_WINDOW_HOURS)
            recent_msgs = await message_repository.list_recent_for_conversation(
                db,
                conversation_id=conv.id,
                since=since,
                exclude_after_id=inbound.id,
                limit=_HISTORY_LIMIT,
            )
            history = _to_chat_history(recent_msgs)
            log.info(
                "history_loaded",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                history_turns=len(history),
            )

            started = time.perf_counter()
            result = await rag_service.answer(
                user_text=parsed.text,
                correlation_id=correlation_id,
                history=history,
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

            tool_calls = result.get("tool_calls") or []
            bot_msg = await message_repository.create_bot(
                db,
                conversation_id=conv.id,
                content=answer_text,
                retrieved_chunks=tool_calls,
                input_tokens=result.get("input_tokens"),
                output_tokens=result.get("output_tokens"),
                latency_ms=latency_ms,
                model_used=settings.openai_model,
                meta_message_id=meta_out_id,
            )

            # SW-30: if the agent invoked escalate_to_human, flip the conversation
            # to takeover so the next inbound skips the bot (see line ~119) and
            # human admins can pick it up. The reason is preserved in conv.meta.
            escalation = next(
                (
                    tc
                    for tc in tool_calls
                    if tc.get("name") == "escalate_to_human"
                ),
                None,
            )
            if escalation is not None:
                reason = str((escalation.get("args") or {}).get("reason", "")).strip()
                conv.status = ConversationStatus.takeover
                conv.meta = {
                    **(conv.meta or {}),
                    "escalation_reason": reason,
                    "escalation_source": "llm",
                    "escalated_at": datetime.now().isoformat(),
                    "escalated_from_message_id": inbound.id,
                }
                log.info(
                    "conversation_escalated",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                    reason=reason,
                    source="llm",
                )

            await db.commit()
            log.info(
                "bot_replied",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                bot_message_id=bot_msg.id,
                latency_ms=latency_ms,
                meta_message_id=meta_out_id,
                escalated=escalation is not None,
            )
        except Exception:
            await db.rollback()
            log.exception(
                "process_failed",
                correlation_id=correlation_id,
                meta_message_id=parsed.meta_message_id,
            )
            raise
        finally:
            # Drain GC while this loop is still alive so transient httpx
            # clients inside ChatOpenAI/OpenAIEmbeddings close their connections
            # here, not in the next task's loop (avoids cosmetic
            # "Event loop is closed" warnings from cross-loop aclose).
            gc.collect()


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
