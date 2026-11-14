"""Resolve durable contacts without treating routing IDs as academic phones."""

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Conversation, Student, WhatsAppIdentity, WhatsAppIdentityEvent
from chatbot_api.repositories.whatsapp_identity import get_alias, lock_identities
from chatbot_api.schemas.whatsapp import ParsedIdentityChange, ParsedInboundMessage
from chatbot_api.services import whatsapp_service
from chatbot_api.services.whatsapp_webhook_service import resolve_identity_scope


class IdentityConflictError(ValueError):
    """Identity or sender ambiguity; fail closed without merging contact histories."""


def validate_sender(sender: str | None) -> None:
    configured = get_settings().meta_phone_number_id
    if sender and configured and sender != configured:
        raise IdentityConflictError("WhatsApp business sender does not match configured sender")


def _timestamp(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError("WhatsApp timestamp must be an integer") from exc


async def _set_phone(db: AsyncSession, student: Student, phone: str | None) -> None:
    student.phone_e164 = phone
    # Retained for API/old readers, never used as the authoritative identity join.
    await db.execute(
        update(Conversation)
        .where(Conversation.student_id == student.id)
        .values(student_phone=phone)
    )


async def resolve_inbound(db: AsyncSession, parsed: ParsedInboundMessage) -> tuple[Student, bool]:
    """Resolve a text observation; caller commits together with the inbound message.

    A new alias may claim a phone-only contact, never a contact with other aliases.
    Known aliases win over phones. Conflicts leave academic associations empty.
    """
    validate_sender(parsed.business_phone_number_id)
    scope = parsed.identity_scope or resolve_identity_scope(
        business_phone_number_id=parsed.business_phone_number_id
    )
    if parsed.from_user_id and not scope:
        raise IdentityConflictError("BSUID requires an identity scope")
    ts = _timestamp(parsed.timestamp)
    await lock_identities(db)
    alias = (
        await get_alias(db, scope, parsed.from_user_id) if scope and parsed.from_user_id else None
    )
    phone_owner = (
        await db.scalar(select(Student).where(Student.phone_e164 == parsed.from_phone))
        if parsed.from_phone
        else None
    )
    student = await db.get(Student, alias.student_id) if alias else None
    created = False
    if student is None:
        student = phone_owner
        if student is not None and parsed.from_user_id:
            has_alias = await db.scalar(
                select(WhatsAppIdentity.id)
                .where(WhatsAppIdentity.student_id == student.id)
                .limit(1)
            )
            if has_alias or (student.whatsapp_scope and student.whatsapp_scope != scope):
                student = None
        if student is None:
            student = Student(phone_e164=parsed.from_phone if phone_owner is None else None)
            db.add(student)
            await db.flush()
            created = True
        if parsed.from_user_id:
            alias = WhatsAppIdentity(
                scope=scope,
                user_id=parsed.from_user_id,
                student_id=student.id,
                business_phone_number_id=parsed.business_phone_number_id,
                parent_user_id=parsed.from_parent_user_id,
                username=parsed.username,
            )
            db.add(alias)
            student.whatsapp_user_id = parsed.from_user_id
            student.whatsapp_scope = scope
    validate_sender(student.business_phone_number_id)
    if (
        student.business_phone_number_id
        and parsed.business_phone_number_id
        and student.business_phone_number_id != parsed.business_phone_number_id
    ):
        raise IdentityConflictError("Contact belongs to another business sender")
    # Retired aliases and delayed pre-rotation messages may contribute history only.
    current = not parsed.from_user_id or parsed.from_user_id == student.whatsapp_user_id
    if current and (created or ts > student.identity_timestamp):
        if parsed.from_phone:
            conflict = phone_owner is not None and phone_owner.id != student.id
            await _set_phone(db, student, None if conflict else parsed.from_phone)
        if parsed.username:
            student.whatsapp_username = parsed.username
            if alias:
                alias.username = parsed.username
        if alias and parsed.from_parent_user_id:
            alias.parent_user_id = parsed.from_parent_user_id
        if parsed.business_phone_number_id:
            student.business_phone_number_id = parsed.business_phone_number_id
        if not student.whatsapp_scope:
            student.whatsapp_scope = scope
        student.identity_timestamp = ts
        # An actual phone observation supersedes the opaque legacy number route.
        if parsed.from_phone:
            student.whatsapp_routing_id = None
    student.last_seen_at = datetime.now()
    if parsed.display_name and not student.display_name:
        student.display_name = parsed.display_name
    await db.flush()
    return student, created


async def apply_identity_change(db: AsyncSession, event: ParsedIdentityChange) -> bool:
    """Apply once, retaining old aliases. Returns False for replay/stale events.

    system.wa_id is an opaque `to` route, never an academic phone. Only subsequent
    actual message.from may establish the new academic association.
    """
    validate_sender(event.business_phone_number_id)
    scope = event.identity_scope or resolve_identity_scope(
        business_phone_number_id=event.business_phone_number_id
    )
    if (event.user_id or event.previous_user_id) and not scope:
        raise IdentityConflictError("BSUID requires an identity scope")
    ts = _timestamp(event.timestamp)
    await lock_identities(db)
    event_scope = scope or "legacy-phone"
    replay = await db.scalar(
        select(WhatsAppIdentityEvent.id).where(
            WhatsAppIdentityEvent.scope == event_scope,
            WhatsAppIdentityEvent.meta_message_id == event.meta_message_id,
        )
    )
    if replay:
        return False
    old = (
        await get_alias(db, scope, event.previous_user_id)
        if scope and event.previous_user_id
        else None
    )
    new = await get_alias(db, scope, event.user_id) if scope and event.user_id else None
    owner = (
        await db.scalar(select(Student).where(Student.phone_e164 == event.from_phone))
        if event.from_phone
        else None
    )
    if old and new and old.student_id != new.student_id:
        raise IdentityConflictError("Rotation aliases belong to different contacts")
    known = old or new
    student = await db.get(Student, known.student_id) if known else owner
    if student is not None and owner is not None and student.id != owner.id:
        raise IdentityConflictError("Rotation phone and alias belong to different contacts")
    if student is None:
        student = Student(phone_e164=None)
        db.add(student)
        await db.flush()
    validate_sender(student.business_phone_number_id)
    if (
        student.business_phone_number_id
        and event.business_phone_number_id
        and student.business_phone_number_id != event.business_phone_number_id
    ):
        raise IdentityConflictError("Rotation sender differs from contact sender")
    if student.whatsapp_scope and student.whatsapp_scope != scope:
        raise IdentityConflictError("Rotation scope differs from contact scope")
    db.add(
        WhatsAppIdentityEvent(
            scope=event_scope, meta_message_id=event.meta_message_id, timestamp=ts
        )
    )
    # Strictly newer changes only: duplicates with different wamids cannot roll
    # back a chain; retired predecessors cannot branch the current destination.
    if ts < student.identity_timestamp or (
        old and student.whatsapp_user_id not in (event.previous_user_id, event.user_id)
    ):
        await db.flush()
        return False
    for user_id, parent in [
        (event.previous_user_id, event.previous_parent_user_id),
        (event.user_id, event.parent_user_id),
    ]:
        if user_id and scope and await get_alias(db, scope, user_id) is None:
            db.add(
                WhatsAppIdentity(
                    scope=scope,
                    user_id=user_id,
                    student_id=student.id,
                    business_phone_number_id=event.business_phone_number_id,
                    parent_user_id=parent,
                )
            )
            await db.flush()
    if event.user_id:
        student.whatsapp_user_id = event.user_id
    student.whatsapp_scope = scope
    if event.business_phone_number_id:
        student.business_phone_number_id = event.business_phone_number_id
    if event.system_type == "user_changed_number":
        await _set_phone(db, student, None)
        student.whatsapp_routing_id = event.new_wa_id
    student.identity_timestamp = ts
    await db.flush()
    return True


async def conversation_contact(db: AsyncSession, conversation_id: int) -> Student:
    student = await db.scalar(
        select(Student)
        .join(Conversation, Conversation.student_id == Student.id)
        .where(Conversation.id == conversation_id)
        .execution_options(populate_existing=True)
    )
    if student is None:
        raise IdentityConflictError("Conversation contact not found")
    validate_sender(student.business_phone_number_id)
    return student


async def current_recipient(
    db: AsyncSession, conversation_id: int, *, academic_phone: str | None = None
) -> dict[str, str]:
    """Fresh destination for delayed/manual sends; never trust queued phone args."""
    student = await conversation_contact(db, conversation_id)
    if academic_phone is not None and student.phone_e164 != academic_phone:
        raise IdentityConflictError("Academic phone changed while preparing the reply")
    if student.whatsapp_user_id:
        expected_scope = resolve_identity_scope()
        if expected_scope != student.whatsapp_scope:
            raise IdentityConflictError("Contact scope differs from configured scope")
        return {"recipient": student.whatsapp_user_id}
    route = student.whatsapp_routing_id or student.phone_e164
    if not route:
        raise IdentityConflictError("Contact has no current WhatsApp destination")
    return {"to": route}


async def send_for_conversation(
    db: AsyncSession,
    *,
    conversation_id: int,
    body: str,
    context: dict[str, Any] | None = None,
    academic_phone: str | None = None,
) -> str:
    recipient = await current_recipient(db, conversation_id, academic_phone=academic_phone)
    return await whatsapp_service.send_message(**recipient, body=body, context=context)
