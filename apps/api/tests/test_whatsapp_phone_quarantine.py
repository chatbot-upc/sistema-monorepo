"""Conflicting phone evidence must invalidate both academic lookup and phone routing."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import (
    Admin,
    Conversation,
    Message,
    MessageRole,
    Student,
    StudentBillingInstallment,
    StudentProfile,
    WhatsAppIdentity,
    WhatsAppPhoneQuarantine,
)
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.services import billing_service, conversation_service
from chatbot_api.services import whatsapp_identity_service as identities
from chatbot_api.workers import conversation as worker

from .factories import make_admin
from .test_whatsapp_identity import inbound


@pytest.fixture(autouse=True)
def configured_sender(monkeypatch):
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "sender-test")
    monkeypatch.setenv("META_BUSINESS_PORTFOLIO_ID", "portfolio-test")
    get_settings.cache_clear()


@pytest.fixture
async def identity_db(postgres_url):
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    token = uuid4().hex
    phone = "+519" + str(int(token[:10], 16))
    alternate = "+519" + str(int(token[:10], 16) + 1)
    try:
        yield factory, token, phone, alternate
    finally:
        async with factory() as db:
            student_ids = (
                await db.scalars(
                    select(Student.id).where(
                        Student.whatsapp_user_id.in_([f"{token}-A", f"{token}-B", f"{token}-C"])
                    )
                )
            ).all()
            await db.execute(
                WhatsAppPhoneQuarantine.__table__.delete().where(
                    WhatsAppPhoneQuarantine.phone_e164.in_([phone, alternate])
                )
            )
            await db.execute(
                Conversation.__table__.delete().where(Conversation.student_id.in_(student_ids))
            )
            await db.execute(
                WhatsAppIdentity.__table__.delete().where(
                    WhatsAppIdentity.student_id.in_(student_ids)
                )
            )
            await db.execute(Student.__table__.delete().where(Student.id.in_(student_ids)))
            await db.execute(
                StudentProfile.__table__.delete().where(
                    StudentProfile.phone_e164.in_([phone, alternate])
                )
            )
            await db.execute(
                StudentBillingInstallment.__table__.delete().where(
                    StudentBillingInstallment.phone_e164.in_([phone, alternate])
                )
            )
            await db.execute(Admin.__table__.delete().where(Admin.email == f"{token}@example.test"))
            await db.commit()
        await engine.dispose()


async def seed_contact(db, user, phone, timestamp):
    student, _ = await identities.resolve_inbound(
        db, inbound(user=user, phone=phone, timestamp=timestamp)
    )
    conv, _, _ = await conversation_repository.get_or_create_open_for_student(db, student.id)
    db.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.student,
            content=f"History {user}",
            retrieved_chunks=[],
        )
    )
    await db.flush()
    return student.id, conv.id


@pytest.mark.parametrize("known_b", [False, True])
@pytest.mark.parametrize("conflict_timestamp", [100, 200])
async def test_conflict_quarantines_phone_across_commits_and_all_contact_flows(
    identity_db, monkeypatch, known_b, conflict_timestamp
):
    factory, token, phone, alternate = identity_db
    user_a, user_b = f"{token}-A", f"{token}-B"
    async with factory() as db:
        a_id, a_conv_id = await seed_contact(db, user_a, phone, 100)
        if known_b:
            await seed_contact(db, user_b, alternate, 100)
        db.add(StudentProfile(phone_e164=phone, full_name="Private academic P"))
        db.add(
            StudentBillingInstallment(
                phone_e164=phone,
                cycle="2026-1",
                number=1,
                concept="Private tuition",
                amount=Decimal("987.65"),
                currency="PEN",
                due_date=date(2026, 11, 1),
            )
        )
        await db.commit()
    async with factory() as db:
        b, _ = await identities.resolve_inbound(
            db, inbound(user=user_b, phone=phone, timestamp=conflict_timestamp)
        )
        b_conv, _, _ = await conversation_repository.get_or_create_open_for_student(db, b.id)
        b_id, b_conv_id = b.id, b_conv.id
        await db.commit()
    assert a_id != b_id and a_conv_id != b_conv_id
    async with factory() as db:
        for sid, cid in [(a_id, a_conv_id), (b_id, b_conv_id)]:
            assert (await db.get(Student, sid)).phone_e164 is None
            assert (await db.get(Conversation, cid)).student_phone is None
            detail = await conversation_service.get_detail(db, cid)
            assert detail.student_phone is None and detail.student_profile is None
        quarantine = await db.get(WhatsAppPhoneQuarantine, phone)
        assert (quarantine.original_student_id, quarantine.conflicting_student_id) == (a_id, b_id)
        assert quarantine.conflict_timestamp == conflict_timestamp
        assert await student_repository.get_by_phone(db, phone) is None

    # Identical/newer repeated claims, including the original owner, do not
    # reclaim a cleared phone. Each request uses a distinct committed transaction.
    for user, timestamp in [
        (user_b, conflict_timestamp),
        (user_b, 300),
        (user_a, 400),
        (f"{token}-C", 500),
    ]:
        async with factory() as db:
            contact, _ = await identities.resolve_inbound(
                db, inbound(user=user, phone=phone, timestamp=timestamp)
            )
            assert contact.phone_e164 is None
            await db.commit()

    monkeypatch.setattr(worker, "_make_session_factory", lambda: factory)
    monkeypatch.setattr(worker, "publish_event", AsyncMock())
    mark_read = AsyncMock()
    send = AsyncMock(side_effect=lambda **_: f"wamid.synthetic.{uuid4().hex}")
    monkeypatch.setattr(worker.whatsapp_service, "mark_read", mark_read)
    monkeypatch.setattr(worker.whatsapp_service, "send_message", send)
    monkeypatch.setattr(
        worker.intent_classifier_service,
        "classify",
        AsyncMock(
            return_value={
                "intent_id": None,
                "intent_name": "consulta_pagos",
                "confidence": 1.0,
                "used_fallback": False,
                "sbert_intent_name": "consulta_pagos",
                "sbert_confidence": 1.0,
            }
        ),
    )
    billing_lookup = AsyncMock(side_effect=AssertionError("Ambiguous phone must not query billing"))
    profile_lookup = AsyncMock(side_effect=AssertionError("Ambiguous phone must not query profile"))
    monkeypatch.setattr(billing_service.student_billing_repository, "list_by_phone", billing_lookup)
    monkeypatch.setattr(worker.student_profile_service, "get_profile_scope", profile_lookup)

    hidden = inbound(user=user_a, timestamp=600)
    await worker._process_async(hidden.model_dump(), "hidden-A-after-conflict")
    assert send.call_args.kwargs["recipient"] == user_a
    assert "No encontré" in send.call_args.kwargs["body"]
    billing_lookup.assert_not_awaited()
    async with factory() as db:
        request = await db.scalar(
            select(Message).where(Message.meta_message_id == hidden.meta_message_id)
        )
        request_id = request.id
        before_messages = (await conversation_service.get_history(db, a_conv_id)).total_messages

    # A queued reply ignores its old phone argument and cannot prepare a profile.
    monkeypatch.setattr(
        worker.rag_service,
        "answer",
        AsyncMock(return_value={"text": "General reply", "tool_calls": []}),
    )
    async with factory() as db:
        await worker._run_reply(
            db,
            conversation_id=a_conv_id,
            phone=phone,
            batch_ids=[request_id],
            correlation_id="delayed-A",
        )
    profile_lookup.assert_not_awaited()
    assert send.call_args.kwargs["recipient"] == user_a
    async with factory() as db:
        with pytest.raises(identities.IdentityConflictError, match="Academic phone changed"):
            await identities.send_for_conversation(
                db,
                conversation_id=a_conv_id,
                body="Prepared academic information",
                academic_phone=phone,
            )
        admin = await make_admin(db, email=f"{token}@example.test")
        monkeypatch.setattr(conversation_service, "publish_event", AsyncMock())
        await conversation_service.send_admin_message(
            db, conversation_id=a_conv_id, body="General manual reply", admin_id=admin.id
        )
    assert send.call_args.kwargs["recipient"] == user_a and "to" not in send.call_args.kwargs

    # The other BSUID remains usable for general chat, with its own history.
    worker.intent_classifier_service.classify.return_value["intent_name"] = None
    await worker._process_async(inbound(user=user_b, timestamp=650).model_dump(), "general-B")
    assert send.call_args.kwargs["recipient"] == user_b
    assert send.call_args.kwargs["body"] == "General reply"
    profile_lookup.assert_not_awaited()

    # Ambiguous phone-only input fails before persistence/classification/sending;
    # old phone entry points cannot silently create an associated contact either.
    send.reset_mock()
    mark_read.reset_mock()
    phone_only = inbound(user=None, phone=phone, timestamp=700)
    with pytest.raises(identities.IdentityConflictError, match="quarantined"):
        await worker._process_async(phone_only.model_dump(), "phone-only-quarantined")
    send.assert_not_awaited()
    mark_read.assert_not_awaited()
    async with factory() as db:
        assert (
            await db.scalar(
                select(Message.id).where(Message.meta_message_id == phone_only.meta_message_id)
            )
            is None
        )
        assert (
            await conversation_service.get_history(db, a_conv_id)
        ).total_messages == before_messages + 2
        with pytest.raises(ValueError, match="quarantined"):
            await student_repository.upsert_by_phone(db, phone_e164=phone)
        with pytest.raises(ValueError, match="quarantined"):
            await conversation_repository.get_or_create_open(db, phone)


@pytest.mark.parametrize("known_b", [False, True])
async def test_stale_conflict_does_not_invalidate_newer_safe_observations(identity_db, known_b):
    factory, token, phone, alternate = identity_db
    async with factory() as db:
        a_id, a_conv_id = await seed_contact(db, f"{token}-A", phone, 300)
        if known_b:
            _, b_conv_id = await seed_contact(db, f"{token}-B", alternate, 400)
        await db.commit()
    async with factory() as db:
        b, _ = await identities.resolve_inbound(
            db, inbound(user=f"{token}-B", phone=phone, timestamp=200)
        )
        assert b.phone_e164 == (alternate if known_b else None)
        assert await db.get(WhatsAppPhoneQuarantine, phone) is None
        a = await db.get(Student, a_id)
        assert a.phone_e164 == phone and a.phone_timestamp == 300
        assert (await db.get(Conversation, a_conv_id)).student_phone == phone
        if known_b:
            assert (await db.get(Conversation, b_conv_id)).student_phone == alternate
        await db.commit()
    async with factory() as db:
        phone_contact, _ = await identities.resolve_inbound(
            db, inbound(user=None, phone=phone, timestamp=350)
        )
        assert phone_contact.id == a_id
        assert await identities.current_recipient(db, a_conv_id) == {"recipient": f"{token}-A"}
        await db.commit()


async def test_recent_conflict_invalidates_prior_owner_but_preserves_claimants_newer_phone(
    identity_db,
):
    factory, token, phone, alternate = identity_db
    async with factory() as db:
        a_id, _ = await seed_contact(db, f"{token}-A", phone, 100)
        b_id, b_conv_id = await seed_contact(db, f"{token}-B", alternate, 300)
        await db.commit()
    async with factory() as db:
        b, _ = await identities.resolve_inbound(
            db, inbound(user=f"{token}-B", phone=phone, timestamp=200)
        )
        assert b.id == b_id and b.phone_e164 == alternate and b.phone_timestamp == 300
        assert (await db.get(Student, a_id)).phone_e164 is None
        assert (await db.get(Conversation, b_conv_id)).student_phone == alternate
        assert await db.get(WhatsAppPhoneQuarantine, phone) is not None
        await db.commit()
