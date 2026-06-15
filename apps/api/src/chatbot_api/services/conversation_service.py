"""Business logic for conversations. Functional module (RORO), no classes."""

from datetime import date, datetime
from math import ceil

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.events import message_to_event_payload, publish_event
from chatbot_api.models import Conversation
from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import build_quoted_snapshot, message_repository
from chatbot_api.repositories.student_profile import student_profile_repository
from chatbot_api.schemas.conversation import (
    ConversationDetail,
    ConversationHistory,
    ConversationListItem,
    SendMessageResponse,
)
from chatbot_api.schemas.message import MessageRead
from chatbot_api.schemas.pagination import Page, PageParams
from chatbot_api.schemas.student_profile import StudentProfileRead
from chatbot_api.services import conversation_history_service, whatsapp_service

log = structlog.get_logger()


async def list_paginated(
    db: AsyncSession,
    *,
    status: ConversationStatus | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    phone: str | None = None,
    pagination: PageParams,
) -> Page[ConversationListItem]:
    rows = await conversation_repository.list_filtered_with_aggregates(
        db,
        status=status,
        from_date=from_date,
        to_date=to_date,
        phone=phone,
        skip=pagination.offset,
        limit=pagination.size,
    )
    total = await conversation_repository.count_filtered(
        db, status=status, from_date=from_date, to_date=to_date, phone=phone
    )

    items = [
        ConversationListItem(
            id=conv.id,
            student_phone=conv.student_phone,
            display_name=profile_name
            or (conv.student.display_name if conv.student else None),
            status=conv.status,
            opened_at=conv.opened_at,
            closed_at=conv.closed_at,
            message_count=msg_count,
            last_message_preview=preview,
            starred=conv.starred,
        )
        for conv, msg_count, preview, profile_name in rows
    ]

    return Page(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )


async def get_detail(db: AsyncSession, conversation_id: int) -> ConversationDetail:
    conv = await conversation_repository.get_with_messages(db, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    detail = ConversationDetail.model_validate(conv)
    detail.display_name = conv.student.display_name if conv.student else None
    detail.email = conv.student.email if conv.student else None
    profile = await student_profile_repository.get_by_phone(db, conv.student_phone)
    if profile is not None:
        detail.student_profile = StudentProfileRead.model_validate(profile)
    return detail


async def set_starred(
    db: AsyncSession, *, conversation_id: int, starred: bool
) -> ConversationDetail:
    conv = await _get_or_404(db, conversation_id)
    conv.starred = starred
    await db.commit()
    return await get_detail(db, conversation_id)


async def update_contact(
    db: AsyncSession, *, conversation_id: int, email: str | None
) -> ConversationDetail:
    conv = await _get_or_404(db, conversation_id)
    normalized = email.strip() if email else None
    conv.student.email = normalized or None
    await db.commit()
    return await get_detail(db, conversation_id)


async def get_history(
    db: AsyncSession, conversation_id: int
) -> ConversationHistory:
    conv = await _get_or_404(db, conversation_id)
    phone = conv.student_phone
    return ConversationHistory(
        total_conversations=await conversation_repository.count_by_phone(db, phone),
        total_messages=await conversation_repository.count_messages_by_phone(
            db, phone
        ),
        first_contact=conv.student.first_seen_at if conv.student else None,
    )


async def list_messages_paginated(
    db: AsyncSession,
    conversation_id: int,
    *,
    pagination: PageParams,
) -> Page[MessageRead]:
    rows = await message_repository.list_by_conversation(
        db, conversation_id, skip=pagination.offset, limit=pagination.size
    )
    total = await message_repository.count_by_conversation(db, conversation_id)
    items = [MessageRead.model_validate(m) for m in rows]
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total else 0,
    )


def _conv_status_payload(
    conv_id: int, conv_status: ConversationStatus, **extra: object
) -> dict[str, object]:
    payload: dict[str, object] = {
        "conversation_id": conv_id,
        "status": conv_status.value,
    }
    payload.update(extra)
    return payload


async def _get_or_404(db: AsyncSession, conversation_id: int) -> Conversation:
    conv = await conversation_repository.get(db, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return conv


async def send_admin_message(
    db: AsyncSession,
    *,
    conversation_id: int,
    body: str,
    admin_id: int,
    in_reply_to_id: int | None = None,
) -> SendMessageResponse:
    """Admin → student via WhatsApp. SW-38.

    Auto-takeover: if conv is `abierta`, switch to `takeover` so the bot stops
    replying. The worker already short-circuits on `status != abierta`, so the
    flip is enough — no extra coordination needed.

    `in_reply_to_id`: cita un mensaje previo de la misma conversación. Se traduce
    su wamid a `context.message_id` para que WhatsApp pinte la cita nativa, y se
    congela el snapshot en el mensaje saliente.
    """
    conv = await _get_or_404(db, conversation_id)
    if conv.status == ConversationStatus.cerrada:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "no se puede responder a una conversación cerrada"
        )

    context: dict[str, str] | None = None
    quoted_snap: dict[str, object] | None = None
    if in_reply_to_id is not None:
        original = await message_repository.get(db, in_reply_to_id)
        if original is None or original.conversation_id != conv.id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "mensaje citado inválido"
            )
        quoted_snap = build_quoted_snapshot(original)
        if original.meta_message_id:
            context = {"message_id": original.meta_message_id}

    meta_id = await whatsapp_service.send_message(
        to=conv.student_phone, body=body, context=context
    )
    msg = await message_repository.create_admin_message(
        db,
        conversation_id=conv.id,
        content=body,
        admin_id=admin_id,
        meta_message_id=meta_id,
        in_reply_to_id=in_reply_to_id,
        quoted=quoted_snap,
    )

    auto_takeover = conv.status == ConversationStatus.abierta
    if auto_takeover:
        conv.status = ConversationStatus.takeover
        conv.takeover_admin = admin_id

    await db.commit()
    await db.refresh(msg)

    await conversation_history_service.append(
        conversation_id=conv.id, messages=[msg]
    )
    await publish_event("message.created", message_to_event_payload(msg))
    if auto_takeover:
        await publish_event(
            "conversation.status_changed",
            _conv_status_payload(
                conv.id, ConversationStatus.takeover, takeover_admin=admin_id
            ),
        )

    log.info(
        "admin_message_sent",
        conversation_id=conv.id,
        admin_id=admin_id,
        message_id=msg.id,
        auto_takeover=auto_takeover,
    )
    return SendMessageResponse(
        message_id=msg.id,
        meta_message_id=meta_id,
        conversation_status=conv.status,
    )


async def takeover(
    db: AsyncSession, *, conversation_id: int, admin_id: int
) -> dict[str, object]:
    """Admin claims a conv. SW-39. Idempotent if already held by same admin."""
    conv = await _get_or_404(db, conversation_id)
    if conv.status == ConversationStatus.cerrada:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "no se puede tomar una conversación cerrada"
        )
    if conv.status == ConversationStatus.takeover and conv.takeover_admin == admin_id:
        return {"status": conv.status.value, "takeover_admin": admin_id}

    conv.status = ConversationStatus.takeover
    conv.takeover_admin = admin_id
    await db.commit()

    await publish_event(
        "conversation.status_changed",
        _conv_status_payload(
            conv.id, ConversationStatus.takeover, takeover_admin=admin_id
        ),
    )
    log.info("conversation_takeover", conversation_id=conv.id, admin_id=admin_id)
    return {"status": conv.status.value, "takeover_admin": admin_id}


async def release(
    db: AsyncSession, *, conversation_id: int, admin_id: int
) -> dict[str, object]:
    """Admin returns conv to bot. Only from takeover."""
    conv = await _get_or_404(db, conversation_id)
    if conv.status != ConversationStatus.takeover:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "solo se puede liberar una conversación en takeover"
        )
    conv.status = ConversationStatus.abierta
    conv.takeover_admin = None
    await db.commit()

    await publish_event(
        "conversation.status_changed",
        _conv_status_payload(conv.id, ConversationStatus.abierta, takeover_admin=None),
    )
    log.info("conversation_released", conversation_id=conv.id, admin_id=admin_id)
    return {"status": conv.status.value}


async def close(
    db: AsyncSession, *, conversation_id: int, admin_id: int
) -> dict[str, object]:
    """Cierra la conversación. Stamps closed_at + closed_by."""
    conv = await _get_or_404(db, conversation_id)
    if conv.status == ConversationStatus.cerrada:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "la conversación ya está cerrada"
        )
    conv.status = ConversationStatus.cerrada
    conv.closed_at = datetime.now()
    conv.closed_by = admin_id
    conv.takeover_admin = None
    await db.commit()

    await publish_event(
        "conversation.status_changed",
        _conv_status_payload(
            conv.id,
            ConversationStatus.cerrada,
            closed_by=admin_id,
            closed_at=conv.closed_at.isoformat(),
        ),
    )
    log.info("conversation_closed", conversation_id=conv.id, admin_id=admin_id)
    return {"status": conv.status.value, "closed_at": conv.closed_at.isoformat()}


async def reopen(
    db: AsyncSession, *, conversation_id: int, admin_id: int
) -> dict[str, object]:
    """Reabre una conv cerrada. Limpia closed_at/closed_by."""
    conv = await _get_or_404(db, conversation_id)
    if conv.status != ConversationStatus.cerrada:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "solo se puede reabrir una conversación cerrada"
        )
    conv.status = ConversationStatus.abierta
    conv.closed_at = None
    conv.closed_by = None
    await db.commit()

    await publish_event(
        "conversation.status_changed",
        _conv_status_payload(conv.id, ConversationStatus.abierta),
    )
    log.info("conversation_reopened", conversation_id=conv.id, admin_id=admin_id)
    return {"status": conv.status.value}


async def delete_conversation(
    db: AsyncSession, *, conversation_id: int, admin_id: int
) -> None:
    """Hard delete de la conversación + sus mensajes (FK cascade). Limpia cache."""
    conv = await _get_or_404(db, conversation_id)
    await db.delete(conv)
    await db.commit()
    await conversation_history_service.clear(conversation_id)
    await publish_event(
        "conversation.deleted", {"conversation_id": conversation_id}
    )
    log.info(
        "conversation_deleted", conversation_id=conversation_id, admin_id=admin_id
    )


