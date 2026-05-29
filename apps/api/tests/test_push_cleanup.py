"""Auto-cleanup of dead FCM tokens (SW-31 polish)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import AdminDevice
from chatbot_api.services import push_service
from tests.factories import make_admin


def test_is_token_dead_recognises_common_fcm_errors() -> None:
    cases = [
        Exception("Requested entity was not found: registration-token-not-registered"),
        Exception("NotRegistered"),
        Exception("InvalidRegistration"),
        Exception("invalid-registration-token: bla"),
        Exception("Mismatched-credential between project and token"),
    ]
    for exc in cases:
        assert push_service._is_token_dead(exc), exc


def test_is_token_dead_ignores_transient_errors() -> None:
    transient = Exception("Internal error: please retry later")
    assert not push_service._is_token_dead(transient)


@pytest.mark.asyncio
async def test_notify_admin_evicts_dead_tokens(
    db_session: AsyncSession,
) -> None:
    admin = await make_admin(db_session, email="push@upc.edu.pe")
    alive = AdminDevice(
        admin_id=admin.id, fcm_token="alive-token", platform="web"
    )
    dead = AdminDevice(
        admin_id=admin.id, fcm_token="dead-token", platform="web"
    )
    db_session.add_all([alive, dead])
    await db_session.flush()

    fake_app = object()

    fake_messaging = MagicMock()

    def _fake_send(message: MagicMock, app: object) -> str:
        if "alive" in getattr(message, "token", ""):
            return "msg-id-ok"
        raise Exception("Requested entity was not found: NotRegistered")

    fake_messaging.send = _fake_send
    fake_messaging.Message = lambda data, token: MagicMock(
        token=token
    )

    with (
        patch.object(push_service, "_get_firebase_app", return_value=fake_app),
        patch.dict("sys.modules", {"firebase_admin.messaging": fake_messaging}),
        patch(
            "firebase_admin.messaging",
            fake_messaging,
            create=True,
        ),
    ):
        sent = await push_service.notify_admin(
            db_session,
            admin_id=admin.id,
            title="hi",
            body="body",
        )

    # 1 alive token still sent successfully; dead one logged + evicted.
    assert sent == 1

    remaining = (
        (await db_session.execute(select(AdminDevice).where(AdminDevice.admin_id == admin.id)))
        .scalars()
        .all()
    )
    tokens = {d.fcm_token for d in remaining}
    assert tokens == {"alive-token"}
