"""Durable identity and isolation regressions; synthetic identities only."""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Conversation, Student, StudentProfile, WhatsAppIdentity
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.schemas.pagination import PageParams
from chatbot_api.schemas.whatsapp import ParsedIdentityChange, ParsedInboundMessage
from chatbot_api.services import billing_service, conversation_service
from chatbot_api.services import whatsapp_identity_service as identities
from chatbot_api.workers import conversation as worker

from .factories import make_admin


@pytest.fixture(autouse=True)
def configured_sender(monkeypatch):
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "sender-test")
    monkeypatch.setenv("META_BUSINESS_PORTFOLIO_ID", "portfolio-test")
    get_settings.cache_clear()


def inbound(*, user="opaque-A", phone=None, timestamp=100, scope="portfolio:portfolio-test", **kw):
    return ParsedInboundMessage(
        meta_message_id=f"wamid.{uuid4().hex}",
        text="hola",
        timestamp=str(timestamp),
        from_phone=phone,
        from_user_id=user,
        identity_scope=scope,
        business_phone_number_id="sender-test",
        **kw,
    )


def rotation(*, old="opaque-A", new="opaque-B", timestamp=200, kind="user_changed_user_id", **kw):
    return ParsedIdentityChange(
        meta_message_id=f"wamid.{uuid4().hex}",
        timestamp=str(timestamp),
        system_type=kind,
        previous_user_id=old,
        user_id=new,
        identity_scope="portfolio:portfolio-test",
        business_phone_number_id="sender-test",
        **kw,
    )


async def test_phone_to_bsuid_continuity_hiding_and_reappearing(db_session):
    student, created = await identities.resolve_inbound(
        db_session, inbound(user=None, phone="+51900008101")
    )
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, student.id
    )
    assert created
    linked, created = await identities.resolve_inbound(
        db_session, inbound(phone=student.phone_e164, timestamp=101, username="student.name")
    )
    assert linked.id == student.id and not created
    hidden, _ = await identities.resolve_inbound(db_session, inbound(timestamp=102))
    same_conv, created, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, hidden.id
    )
    assert same_conv.id == conv.id and not created
    assert hidden.phone_e164 == "+51900008101"
    assert await identities.current_recipient(db_session, conv.id) == {"recipient": "opaque-A"}
    again, _ = await identities.resolve_inbound(
        db_session, inbound(phone="+51900008101", timestamp=103)
    )
    assert again.id == student.id
    page = await conversation_service.list_paginated(db_session, pagination=PageParams())
    item = next(i for i in page.items if i.id == conv.id)
    assert item.student_id == student.id and item.whatsapp_username == "student.name"


async def test_rotations_replay_old_alias_and_phone_confirmation(db_session):
    student, _ = await identities.resolve_inbound(db_session, inbound(phone="+51900008102"))
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, student.id
    )
    event = rotation(
        kind="user_changed_number", from_phone=student.phone_e164, new_wa_id="51911111111"
    )
    assert await identities.apply_identity_change(db_session, event)
    assert student.phone_e164 is None and conv.student_phone is None
    assert student.whatsapp_routing_id == "51911111111"
    assert not await identities.apply_identity_change(db_session, event)
    assert await identities.current_recipient(db_session, conv.id) == {"recipient": "opaque-B"}
    stale, _ = await identities.resolve_inbound(
        db_session, inbound(phone="+51900008102", timestamp=150)
    )
    assert stale.id == student.id and stale.phone_e164 is None
    # Even a later message through the historical alias must not undo rotation.
    await identities.resolve_inbound(db_session, inbound(phone="+51900008102", timestamp=250))
    assert student.whatsapp_user_id == "opaque-B" and student.phone_e164 is None
    await identities.resolve_inbound(
        db_session, inbound(user="opaque-B", phone="+51900008103", timestamp=300)
    )
    assert student.phone_e164 == "+51900008103"
    newer = rotation(old="opaque-B", new="opaque-C", timestamp=400)
    await identities.apply_identity_change(db_session, newer)
    assert not await identities.apply_identity_change(
        db_session,
        event.model_copy(update={"meta_message_id": "replayed-other-id", "timestamp": "500"}),
    )
    assert await identities.current_recipient(db_session, conv.id) == {"recipient": "opaque-C"}
    aliases = (
        await db_session.scalars(
            select(WhatsAppIdentity.user_id).where(WhatsAppIdentity.student_id == student.id)
        )
    ).all()
    assert set(aliases) == {"opaque-A", "opaque-B", "opaque-C"}


async def test_phone_only_rotation_keeps_opaque_route_out_of_profile(db_session):
    student, _ = await identities.resolve_inbound(
        db_session, inbound(user=None, phone="+51900008104")
    )
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, student.id
    )
    await identities.apply_identity_change(
        db_session,
        rotation(
            old=None,
            new=None,
            kind="user_changed_number",
            from_phone=student.phone_e164,
            new_wa_id="route.opaque",
        ),
    )
    assert student.phone_e164 is None
    assert await identities.current_recipient(db_session, conv.id) == {"to": "route.opaque"}
    detail = await conversation_service.get_detail(db_session, conv.id)
    assert detail.student_phone is None and detail.student_profile is None


async def test_conflicts_do_not_merge_history_or_academic_profile(db_session):
    first, _ = await identities.resolve_inbound(db_session, inbound(phone="+51900008105"))
    first_conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, first.id
    )
    db_session.add(StudentProfile(phone_e164=first.phone_e164, full_name="Private profile"))
    await db_session.flush()
    other, _ = await identities.resolve_inbound(
        db_session, inbound(user="different", phone=first.phone_e164)
    )
    other_conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, other.id
    )
    assert other.id != first.id and other.phone_e164 is None and other_conv.id != first_conv.id
    detail = await conversation_service.get_detail(db_session, other_conv.id)
    assert detail.student_profile is None and detail.student_phone is None
    with pytest.raises(identities.IdentityConflictError):
        await identities.apply_identity_change(db_session, rotation(new="different"))
    assert first.whatsapp_user_id == "opaque-A" and other.whatsapp_user_id == "different"
    # Existing alias plus a different contact's phone cannot carry its own stale profile either.
    third, _ = await identities.resolve_inbound(
        db_session, inbound(user="third", phone="+51900008106")
    )
    await identities.resolve_inbound(
        db_session, inbound(user="third", phone=first.phone_e164, timestamp=101)
    )
    assert third.phone_e164 is None


async def test_same_bsuid_separate_scopes_and_sender_mismatch(db_session):
    one, _ = await identities.resolve_inbound(db_session, inbound())
    two, _ = await identities.resolve_inbound(db_session, inbound(scope="portfolio:another"))
    assert one.id != two.id
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(db_session, two.id)
    with pytest.raises(identities.IdentityConflictError, match="scope"):
        await identities.current_recipient(db_session, conv.id)
    with pytest.raises(identities.IdentityConflictError, match="sender"):
        await identities.resolve_inbound(
            db_session, inbound().model_copy(update={"business_phone_number_id": "other-sender"})
        )


@pytest.mark.parametrize("use_bsuid", [True, False])
async def test_concurrent_first_messages_share_contact_and_conversation(postgres_url, use_bsuid):
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    unique = uuid4().hex
    parsed = inbound(
        user=unique if use_bsuid else None,
        phone=None if use_bsuid else "+519" + str(int(unique[:10], 16)),
    )

    async def resolve():
        async with factory() as db:
            student, _ = await identities.resolve_inbound(db, parsed)
            conv, _, _ = await conversation_repository.get_or_create_open_for_student(
                db, student.id
            )
            await db.commit()
            return student.id, conv.id

    try:
        results = await asyncio.gather(resolve(), resolve(), resolve())
        assert len(set(results)) == 1
    finally:
        async with factory() as db:
            sid, _ = results[0]
            await db.execute(Conversation.__table__.delete().where(Conversation.student_id == sid))
            await db.execute(
                WhatsAppIdentity.__table__.delete().where(WhatsAppIdentity.student_id == sid)
            )
            await db.execute(Student.__table__.delete().where(Student.id == sid))
            await db.commit()
        await engine.dispose()


async def test_manual_send_bsuid_and_delayed_reply_refresh_recipient(db_session, monkeypatch):
    student, _ = await identities.resolve_inbound(db_session, inbound(phone="+51900008107"))
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, student.id
    )
    admin = await make_admin(db_session)
    await identities.apply_identity_change(db_session, rotation())
    send = AsyncMock(return_value="wamid.synthetic.manual")
    monkeypatch.setattr(identities.whatsapp_service, "send_message", send)
    monkeypatch.setattr(conversation_service, "publish_event", AsyncMock())
    await conversation_service.send_admin_message(
        db_session, conversation_id=conv.id, body="Manual reply", admin_id=admin.id
    )
    assert send.call_args.kwargs["recipient"] == "opaque-B"
    assert "to" not in send.call_args.kwargs
    history = await conversation_service.get_history(db_session, conv.id)
    assert history.total_messages == 1
    # The same recipient resolver is used by queued generate_reply; see worker test below.


async def test_bsuid_only_worker_general_reply_and_no_academic_lookup(db_session, monkeypatch):
    # Share the rollback-scoped fixture session while exercising the real worker.
    class SessionContext:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(worker, "_make_session_factory", lambda: SessionContext)
    monkeypatch.setattr(worker, "publish_event", AsyncMock())
    monkeypatch.setattr(worker.whatsapp_service, "mark_read", AsyncMock())
    classify = AsyncMock(
        return_value={
            "intent_id": None,
            "intent_name": None,
            "confidence": 0.0,
            "used_fallback": False,
            "sbert_intent_name": None,
            "sbert_confidence": 0.0,
        }
    )
    monkeypatch.setattr(worker.intent_classifier_service, "classify", classify)
    monkeypatch.setattr(
        worker.rag_service,
        "answer",
        AsyncMock(return_value={"text": "General information", "tool_calls": []}),
    )
    profile = AsyncMock(side_effect=AssertionError("No academic lookup for unknown phone"))
    monkeypatch.setattr(worker.student_profile_service, "get_profile_scope", profile)
    send = AsyncMock(side_effect=["wamid.welcome", "wamid.general", "wamid.delayed"])
    monkeypatch.setattr(worker.whatsapp_service, "send_message", send)
    parsed = inbound()
    await worker._process_async(parsed.model_dump(), "test")
    assert send.await_count == 2
    assert all(
        c.kwargs["recipient"] == "opaque-A" and "to" not in c.kwargs for c in send.call_args_list
    )
    conv = await db_session.scalar(
        select(Conversation).join(Student).where(Student.whatsapp_user_id == "opaque-A")
    )
    assert conv.student_phone is None
    from chatbot_api.models import Message

    msg = await db_session.scalar(
        select(Message).where(Message.meta_message_id == parsed.meta_message_id)
    )
    await identities.apply_identity_change(db_session, rotation())
    await db_session.commit()
    await worker._run_reply(
        db_session,
        conversation_id=conv.id,
        phone="+51999999999",
        batch_ids=[msg.id],
        correlation_id="old-job",
    )
    assert send.call_args.kwargs["recipient"] == "opaque-B"
    profile.assert_not_awaited()
    with patch.object(
        billing_service.student_billing_repository,
        "list_by_phone",
        AsyncMock(side_effect=AssertionError("No billing lookup")),
    ):
        assert "No encontré" in await billing_service.build_payment_reply(
            db_session, phone_e164=None
        )


async def test_stale_current_alias_cannot_restore_phone(db_session):
    student, _ = await identities.resolve_inbound(db_session, inbound(phone="+51900008108"))
    await identities.apply_identity_change(
        db_session,
        rotation(
            new="opaque-A",
            kind="user_changed_number",
            from_phone=student.phone_e164,
            new_wa_id="51900008109",
        ),
    )
    await identities.resolve_inbound(db_session, inbound(phone="+51900008108", timestamp=150))
    assert student.phone_e164 is None


async def test_same_second_phone_rotation_requires_later_phone_observation(db_session):
    student, _ = await identities.resolve_inbound(db_session, inbound(phone="+51900008110"))
    assert await identities.apply_identity_change(
        db_session,
        rotation(
            new="opaque-A",
            timestamp=100,
            kind="user_changed_number",
            from_phone=student.phone_e164,
            new_wa_id="51900008111",
        ),
    )
    await identities.resolve_inbound(db_session, inbound(phone="+51900008110", timestamp=100))
    assert student.phone_e164 is None
    await identities.resolve_inbound(db_session, inbound(phone="+51900008111", timestamp=101))
    assert student.phone_e164 == "+51900008111"


async def test_out_of_order_unknown_chain_fails_closed_without_merge(db_session):
    original, _ = await identities.resolve_inbound(db_session, inbound(phone="+51900008112"))
    original_conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, original.id
    )
    await identities.apply_identity_change(
        db_session, rotation(old="opaque-B", new="opaque-C", timestamp=300)
    )
    newer, _ = await identities.resolve_inbound(db_session, inbound(user="opaque-C", timestamp=301))
    newer_conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, newer.id
    )
    with pytest.raises(identities.IdentityConflictError):
        await identities.apply_identity_change(db_session, rotation(timestamp=200))
    assert newer.id != original.id and newer.phone_e164 is None
    assert newer_conv.id != original_conv.id
    assert (
        await conversation_service.get_detail(db_session, newer_conv.id)
    ).student_profile is None


async def test_academic_reply_prepared_before_rotation_is_not_sent(db_session, monkeypatch):
    student, _ = await identities.resolve_inbound(db_session, inbound(phone="+51900008113"))
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, student.id
    )
    previous_phone = student.phone_e164
    await identities.apply_identity_change(
        db_session,
        rotation(kind="user_changed_number", from_phone=previous_phone, new_wa_id="51900008114"),
    )
    send = AsyncMock()
    monkeypatch.setattr(identities.whatsapp_service, "send_message", send)
    with pytest.raises(identities.IdentityConflictError, match="Academic phone changed"):
        await identities.send_for_conversation(
            db_session,
            conversation_id=conv.id,
            body="Old academic information",
            academic_phone=previous_phone,
        )
    send.assert_not_awaited()


async def test_inbound_quote_cannot_copy_another_contacts_history(db_session, monkeypatch):
    from chatbot_api.models import Message, MessageRole

    student, _ = await identities.resolve_inbound(db_session, inbound())
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, student.id
    )
    other, _ = await identities.resolve_inbound(db_session, inbound(user="unrelated"))
    other_conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, other.id
    )
    secret = Message(
        conversation_id=other_conv.id,
        role=MessageRole.bot,
        content="Private academic info",
        meta_message_id="wamid.private",
        retrieved_chunks=[],
    )
    db_session.add(secret)
    await db_session.flush()

    class SessionContext:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(worker, "_make_session_factory", lambda: SessionContext)
    monkeypatch.setattr(worker, "publish_event", AsyncMock())
    monkeypatch.setattr(worker.whatsapp_service, "mark_read", AsyncMock())
    monkeypatch.setattr(worker, "_run_reply", AsyncMock())
    monkeypatch.setattr(
        worker.intent_classifier_service,
        "classify",
        AsyncMock(
            return_value={
                "intent_id": None,
                "intent_name": None,
                "confidence": 0.0,
                "used_fallback": False,
                "sbert_intent_name": None,
                "sbert_confidence": 0.0,
            }
        ),
    )
    parsed = inbound(context_wamid="wamid.private", timestamp=101)
    await worker._process_async(parsed.model_dump(), "quote-isolation")
    stored = await db_session.scalar(
        select(Message).where(Message.meta_message_id == parsed.meta_message_id)
    )
    assert stored.conversation_id == conv.id
    assert stored.in_reply_to_id is None and stored.quoted is None


async def test_persisted_foreign_sender_cannot_send_after_configuration_change(
    db_session, monkeypatch
):
    student, _ = await identities.resolve_inbound(db_session, inbound())
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(
        db_session, student.id
    )
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "different-sender")
    get_settings.cache_clear()
    send = AsyncMock()
    monkeypatch.setattr(identities.whatsapp_service, "send_message", send)
    with pytest.raises(identities.IdentityConflictError, match="sender"):
        await identities.send_for_conversation(
            db_session, conversation_id=conv.id, body="Must not cross senders"
        )
    send.assert_not_awaited()
