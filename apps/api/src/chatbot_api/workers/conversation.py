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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.celery_app import celery_app
from chatbot_api.core.events import message_to_event_payload, publish_event
from chatbot_api.core.settings import get_settings
from chatbot_api.models import ConversationIntent
from chatbot_api.models.enums import ConversationStatus, MessageRole
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import build_quoted_snapshot, message_repository
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


_PENDING_KEY = "chatbot:reply_pending:"
_TOKEN_KEY = "chatbot:reply_token:"  # noqa: S105 — Redis key prefix, no secreto
_DEBOUNCE_TTL = 3600


async def _push_pending_and_bump(conv_id: int, message_id: int) -> str | None:
    """Encola el mensaje al lote pendiente y reinicia la ventana (nuevo token).

    Devuelve el token agendado, o None si Redis falla (el caller degrada a inline).
    """
    settings = get_settings()
    token = uuid.uuid4().hex
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url)
        try:
            pipe = client.pipeline(transaction=True)
            pipe.rpush(f"{_PENDING_KEY}{conv_id}", message_id)
            pipe.expire(f"{_PENDING_KEY}{conv_id}", _DEBOUNCE_TTL)
            pipe.set(f"{_TOKEN_KEY}{conv_id}", token, ex=_DEBOUNCE_TTL)
            await pipe.execute()
        finally:
            await client.aclose()
        return token
    except Exception:
        log.exception("reply_debounce_push_failed", conversation_id=conv_id)
        return None


async def _drain_pending_if_current(conv_id: int, token: str) -> list[int] | None:
    """Si `token` sigue siendo el vigente, drena y devuelve los ids del lote.

    Devuelve None si el token fue superado por un mensaje más nuevo (este task
    debe abortar) o si Redis falla.
    """
    settings = get_settings()
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url)
        try:
            current = await client.get(f"{_TOKEN_KEY}{conv_id}")
            if isinstance(current, bytes):
                current = current.decode("utf-8")
            if current != token:
                return None  # superado por un mensaje posterior
            pipe = client.pipeline(transaction=True)
            pipe.lrange(f"{_PENDING_KEY}{conv_id}", 0, -1)
            pipe.delete(f"{_PENDING_KEY}{conv_id}")
            pipe.delete(f"{_TOKEN_KEY}{conv_id}")
            raw, _, _ = await pipe.execute()
        finally:
            await client.aclose()
        return [int(x) for x in raw]
    except Exception:
        log.exception("reply_debounce_drain_failed", conversation_id=conv_id)
        return None


async def _run_reply(
    db: Any,
    *,
    conversation_id: int,
    phone: str,
    batch_ids: list[int],
    correlation_id: str,
) -> None:
    """Genera UNA respuesta de Remi para el lote consolidado de mensajes.

    Compartido por la ruta inline (debounce off) y la ruta debounced. Consolida
    los mensajes del estudiante en un solo turno, corre el RAG, y cita el primer
    mensaje del lote solo si hubo varios (varias preguntas → ancla la respuesta).
    """
    settings = get_settings()
    conv = await conversation_repository.get(db, conversation_id)
    if conv is None or conv.status != ConversationStatus.abierta:
        log.info(
            "reply_skipped_not_open",
            correlation_id=correlation_id,
            conversation_id=conversation_id,
            status=getattr(conv, "status", None),
        )
        return

    batch = sorted(
        (
            m
            for m in await message_repository.list_by_ids(db, batch_ids)
            if m.role == MessageRole.student
        ),
        key=lambda m: m.id,
    )
    if not batch:
        return
    consolidated = "\n".join(m.content for m in batch if m.content)
    if not consolidated:
        return

    history = await conversation_history_service.get(
        db,
        conversation_id=conversation_id,
        exclude_message_id=batch[0].id,
    )

    # SW-48/SW-46: perfil académico + carrera para personalizar y scopear el RAG.
    profile_context, program = await student_profile_service.get_profile_scope(
        db, phone
    )

    # Texto del turno para el agente. Si hubo varios mensajes, los numeramos y le
    # ofrecemos citar uno concreto vía la tool reply_to_message — la decisión de
    # si cita y a cuál la toma el LLM según el contexto (no una regla fija).
    if len(batch) > 1:
        numbered = "\n".join(f"{i + 1}. {m.content}" for i, m in enumerate(batch))
        agent_user_text = (
            "El estudiante te escribió varios mensajes seguidos (numerados abajo). "
            "Respóndelos de forma natural y unificada. Si UNO de ellos contiene la "
            "consulta o intención principal, cítalo llamando a reply_to_message con "
            "su número — elige el mensaje con la pregunta concreta, NO saludos ni "
            "relleno como 'hola', 'buenas' o 'qué tal'. Si ninguno destaca (p. ej. "
            "solo saludos), no cites.\n\n"
            f"{numbered}"
        )
    else:
        agent_user_text = consolidated

    # Si algún mensaje del lote citaba un mensaje previo nuestro, anclamos ese
    # texto (reusamos el snapshot ya guardado, sin query nueva) para precisión.
    cited = next((m.quoted for m in reversed(batch) if m.quoted), None)
    if cited and cited.get("content"):
        autor = (
            "ti (el asistente)"
            if cited.get("role") != MessageRole.student.value
            else "el estudiante"
        )
        agent_user_text = (
            f"[El estudiante está respondiendo a este mensaje previo de "
            f'{autor}: "{str(cited["content"])[:300]}"]\n\n{agent_user_text}'
        )

    # "Escribiendo…" mientras corre el RAG (se descarta al enviar la respuesta o
    # a los ~25s). Lo anclamos al último mensaje del lote. Best-effort.
    if batch[-1].meta_message_id:
        await whatsapp_service.mark_read(
            message_id=batch[-1].meta_message_id, typing=True
        )

    started = time.perf_counter()
    result = await rag_service.answer(
        user_text=agent_user_text,
        correlation_id=correlation_id,
        history=history,
        db=db,
        profile_context=profile_context,
        program=program,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    answer_text = str(result.get("text") or "")
    if not answer_text:
        log.warning(
            "rag_empty_answer",
            correlation_id=correlation_id,
            conversation_id=conversation_id,
        )
        return

    tool_calls = result.get("tool_calls") or []

    # Cita: la decide el agente. Si llamó reply_to_message(n) con un n válido del
    # lote, Remi cita ese mensaje (solo si tiene wamid). Si no la llamó, no cita.
    quote_target = None
    if len(batch) > 1:
        for tc in tool_calls:
            if tc.get("name") != "reply_to_message":
                continue
            raw_n = (tc.get("args") or {}).get("message_number")
            if raw_n is None:
                continue
            try:
                n = int(raw_n)
            except (TypeError, ValueError):
                continue
            if 1 <= n <= len(batch):
                quote_target = batch[n - 1]
    # El narrowing de quote_target (Message | None) se hace dentro del if para
    # que mypy lo estreche a Message al construir el contexto/snapshot de la cita.
    should_quote = False
    reply_context: dict[str, str] | None = None
    in_reply_to_id: int | None = None
    quoted_snapshot: dict[str, object] | None = None
    if quote_target is not None and quote_target.meta_message_id:
        should_quote = True
        reply_context = {"message_id": quote_target.meta_message_id}
        in_reply_to_id = quote_target.id
        quoted_snapshot = build_quoted_snapshot(quote_target)

    meta_out_id = await whatsapp_service.send_message(
        to=phone, body=answer_text, context=reply_context
    )

    bot_msg = await message_repository.create_bot(
        db,
        conversation_id=conversation_id,
        content=answer_text,
        retrieved_chunks=tool_calls,
        input_tokens=result.get("input_tokens"),
        output_tokens=result.get("output_tokens"),
        latency_ms=latency_ms,
        model_used=settings.openai_model,
        meta_message_id=meta_out_id,
        in_reply_to_id=in_reply_to_id,
        quoted=quoted_snapshot,
    )

    # SW-30: si el agente invocó escalate_to_human, pasamos a takeover.
    escalation = next(
        (tc for tc in tool_calls if tc.get("name") == "escalate_to_human"),
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
            "escalated_from_message_id": batch[-1].id,
        }
        log.info(
            "conversation_escalated",
            correlation_id=correlation_id,
            conversation_id=conversation_id,
            reason=reason,
            source="llm",
        )
        await _send_escalation_side_effects(
            db,
            conv_id=conversation_id,
            student_phone=phone,
            inbound_id=batch[-1].id,
            inbound_text=consolidated,
            reason=reason,
            source="llm",
            notify_student=False,
            correlation_id=correlation_id,
        )

    await db.commit()
    await conversation_history_service.append(
        conversation_id=conversation_id, messages=[*batch, bot_msg]
    )
    await publish_event("message.created", message_to_event_payload(bot_msg))
    if escalation is not None:
        await publish_event(
            "conversation.status_changed",
            {"conversation_id": conversation_id, "status": "takeover"},
        )
    log.info(
        "bot_replied",
        correlation_id=correlation_id,
        conversation_id=conversation_id,
        bot_message_id=bot_msg.id,
        latency_ms=latency_ms,
        meta_message_id=meta_out_id,
        batch_size=len(batch),
        quoted=should_quote,
        escalated=escalation is not None,
    )


async def _generate_reply_async(
    conversation_id: int, phone: str, token: str, correlation_id: str
) -> None:
    """Entry de la ruta debounced: si el token vence, drena el lote y responde."""
    ids = await _drain_pending_if_current(conversation_id, token)
    if not ids:
        log.info(
            "reply_superseded",
            correlation_id=correlation_id,
            conversation_id=conversation_id,
        )
        return
    factory = _make_session_factory()
    async with factory() as db:
        try:
            await _run_reply(
                db,
                conversation_id=conversation_id,
                phone=phone,
                batch_ids=ids,
                correlation_id=correlation_id,
            )
        except Exception:
            await db.rollback()
            log.exception(
                "generate_reply_failed",
                correlation_id=correlation_id,
                conversation_id=conversation_id,
            )
            raise
        finally:
            gc.collect()


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
            (
                conv,
                conv_created,
                conv_reopened,
            ) = await conversation_repository.get_or_create_open(
                db, parsed.from_phone
            )
            if conv_created:
                # Conv brand-new: limpiar cualquier cache stale de una posible
                # encarnación previa con el mismo id (DB reset, etc.) para
                # evitar contaminar el contexto del RAG.
                await conversation_history_service.clear(conv.id)

            # Cita/reply entrante: si el estudiante citó un mensaje nuestro, Meta
            # manda context.id (= wamid). Lo resolvemos a nuestro id interno y
            # congelamos el snapshot. `original` se reutiliza abajo para darle al
            # agente AI el contexto exacto del mensaje citado (sin otra query).
            in_reply_to_id: int | None = None
            quoted_snap: dict[str, object] | None = None
            original = None
            if parsed.context_wamid:
                original = await message_repository.get_by_meta_id(
                    db, parsed.context_wamid
                )
                if original is not None:
                    in_reply_to_id = original.id
                    quoted_snap = build_quoted_snapshot(original)

            inbound = await message_repository.create_inbound(
                db,
                conversation_id=conv.id,
                content=parsed.text,
                meta_message_id=parsed.meta_message_id,
                in_reply_to_id=in_reply_to_id,
                quoted=quoted_snap,
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
            # Acuse de lectura (✓✓ azul) al instante, sin esperar la ventana de
            # debounce. Best-effort: no rompe el flujo si Meta falla.
            await whatsapp_service.mark_read(message_id=parsed.meta_message_id)
            if conv_reopened:
                # El CRM debe ver el pill "Cerrada" → "Abierta" en vivo.
                await publish_event(
                    "conversation.status_changed",
                    {"conversation_id": conv.id, "status": "abierta"},
                )
            log.info(
                "inbound_persisted",
                correlation_id=correlation_id,
                conversation_id=conv.id,
                message_id=inbound.id,
                conversation_created=conv_created,
                conversation_reopened=conv_reopened,
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

            # Debounce: en vez de responder inline, agrupamos mensajes rápidos en
            # un solo turno. Cada mensaje reinicia la ventana (bump del token); el
            # task del último mensaje gana, consolida el lote y responde una vez.
            # Si el debounce está off (tests) respondemos inline al toque.
            if settings.reply_debounce_enabled:
                token = await _push_pending_and_bump(conv.id, inbound.id)
                if token is not None:
                    generate_reply.apply_async(
                        (conv.id, parsed.from_phone, token, correlation_id),
                        countdown=settings.reply_debounce_seconds,
                    )
                    log.info(
                        "reply_scheduled",
                        correlation_id=correlation_id,
                        conversation_id=conv.id,
                        message_id=inbound.id,
                        debounce_seconds=settings.reply_debounce_seconds,
                    )
                    return
                # Redis no disponible → degradar a respuesta inmediata inline.
                log.warning(
                    "reply_debounce_unavailable_inline",
                    correlation_id=correlation_id,
                    conversation_id=conv.id,
                )
            await _run_reply(
                db,
                conversation_id=conv.id,
                phone=parsed.from_phone,
                batch_ids=[inbound.id],
                correlation_id=correlation_id,
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


@celery_app.task(  # type: ignore[untyped-decorator]
    name="generate_reply",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def generate_reply(
    self: Any,
    conversation_id: int,
    phone: str,
    token: str,
    correlation_id: str,
) -> None:
    """Task debounced: responde al lote consolidado si su token sigue vigente."""
    asyncio.run(
        _generate_reply_async(conversation_id, phone, token, correlation_id)
    )
