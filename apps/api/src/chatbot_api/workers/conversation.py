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
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.celery_app import celery_app
from chatbot_api.core.events import message_to_event_payload, publish_event
from chatbot_api.core.settings import get_settings
from chatbot_api.models import ConversationIntent
from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.services import (
    conversation_history_service,
    intent_classifier_service,
    push_service,
    rag_service,
    student_profile_service,
    whatsapp_service,
)

log = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v1"
_WELCOME_PATH = _PROMPTS_DIR / "welcome.md"
_ESCALATION_NOTICE_PATH = _PROMPTS_DIR / "escalation_notice.md"
_welcome_text: str | None = None
_escalation_notice: str | None = None


def _get_welcome_text() -> str:
    global _welcome_text
    if _welcome_text is None:
        _welcome_text = _WELCOME_PATH.read_text(encoding="utf-8").strip()
    return _welcome_text


def _get_escalation_notice() -> str:
    global _escalation_notice
    if _escalation_notice is None:
        _escalation_notice = _ESCALATION_NOTICE_PATH.read_text(encoding="utf-8").strip()
    return _escalation_notice


def _make_session_factory() -> async_sessionmaker[Any]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


_PUSH_BODY_LIMIT = 140


async def _send_escalation_side_effects(
    db: Any,
    *,
    conv_id: int,
    student_phone: str,
    inbound_id: int,
    inbound_text: str,
    reason: str,
    source: str,
    notify_student: bool,
    correlation_id: str,
) -> None:
    """SW-29 + SW-31 side effects.

    - notify_student=True: send a fixed escalation notice to the student and
      persist it as a bot message (used by the deterministic SBERT path).
      The LLM path lets the agent write its own farewell, so it skips this.
    - Always: broadcast a push to every active admin with the student phone,
      inbound text, conversation id, and reason.
    """
    if notify_student:
        notice = _get_escalation_notice()
        try:
            meta_id = await whatsapp_service.send_message(
                to=student_phone, body=notice
            )
        except Exception:
            log.exception(
                "escalation_notice_send_failed",
                correlation_id=correlation_id,
                conversation_id=conv_id,
            )
        else:
            await message_repository.create_bot(
                db,
                conversation_id=conv_id,
                content=notice,
                meta_message_id=meta_id,
            )
            # Notice canned tampoco entra al cache (mismo motivo que welcome).
            log.info(
                "escalation_notice_sent",
                correlation_id=correlation_id,
                conversation_id=conv_id,
                meta_message_id=meta_id,
            )

    try:
        push_body = inbound_text[:_PUSH_BODY_LIMIT]
        sent = await push_service.notify_all_admins(
            db,
            title=f"🔔 Derivada · {student_phone}",
            body=push_body,
            data={
                "type": "escalation",
                "conversation_id": str(conv_id),
                "student_phone": student_phone,
                "message_id": str(inbound_id),
                "reason": reason,
                "source": source,
                "url": f"/conversations/{conv_id}",
            },
        )
        log.info(
            "escalation_push_dispatched",
            correlation_id=correlation_id,
            conversation_id=conv_id,
            push_sent=sent,
            source=source,
        )
    except Exception:
        log.exception(
            "escalation_push_failed",
            correlation_id=correlation_id,
            conversation_id=conv_id,
        )


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
            if conv_created:
                # Conv brand-new: limpiar cualquier cache stale de una posible
                # encarnación previa con el mismo id (DB reset, etc.) para
                # evitar contaminar el contexto del RAG.
                await conversation_history_service.clear(conv.id)

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
            await publish_event(
                "message.created", message_to_event_payload(inbound)
            )
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
                await publish_event(
                    "conversation.escalated",
                    {
                        "conversation_id": conv.id,
                        "source": "intent_classifier",
                        "reason": "intent:solicita_humano",
                    },
                )
                await publish_event(
                    "conversation.status_changed",
                    {"conversation_id": conv.id, "status": "takeover"},
                )
                log.info(
                    "conversation_escalated",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                    reason="intent:solicita_humano",
                    source="intent_classifier",
                )
                # SW-29: student gets a fixed notice (LLM didn't generate one).
                # SW-31: admins receive a push with full context.
                await _send_escalation_side_effects(
                    db,
                    conv_id=conv.id,
                    student_phone=parsed.from_phone,
                    inbound_id=inbound.id,
                    inbound_text=parsed.text,
                    reason="intent:solicita_humano",
                    source="intent_classifier",
                    notify_student=True,
                    correlation_id=correlation_id,
                )
                await db.commit()
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
                # Welcome NO entra al cache: es scaffolding (saludo canned),
                # no aporta contexto útil al RAG en turnos futuros.
                await publish_event(
                    "message.created", message_to_event_payload(welcome_msg)
                )
                log.info(
                    "welcome_sent",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                    bot_message_id=welcome_msg.id,
                    meta_message_id=welcome_meta_id,
                )

            history = await conversation_history_service.get(
                db,
                conversation_id=conv.id,
                exclude_message_id=inbound.id,
            )
            log.info(
                "history_loaded",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                history_turns=len(history),
            )

            # SW-48: cargar perfil académico por número para personalizar.
            profile_context = await student_profile_service.get_profile_context(
                db, parsed.from_phone
            )
            log.info(
                "profile_loaded",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                profile_loaded=profile_context is not None,
            )

            started = time.perf_counter()
            result = await rag_service.answer(
                user_text=parsed.text,
                correlation_id=correlation_id,
                history=history,
                db=db,
                profile_context=profile_context,
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
                # SW-31: admins receive push. Student already got the LLM
                # answer (which typically explains the handoff), so we skip
                # the canned notice to avoid two messages back-to-back.
                await _send_escalation_side_effects(
                    db,
                    conv_id=conv.id,
                    student_phone=parsed.from_phone,
                    inbound_id=inbound.id,
                    inbound_text=parsed.text,
                    reason=reason,
                    source="llm",
                    notify_student=False,
                    correlation_id=correlation_id,
                )

            await db.commit()
            await conversation_history_service.append(
                conversation_id=conv.id, messages=[inbound, bot_msg]
            )
            await publish_event(
                "message.created", message_to_event_payload(bot_msg)
            )
            if escalation is not None:
                await publish_event(
                    "conversation.status_changed",
                    {"conversation_id": conv.id, "status": "takeover"},
                )
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
