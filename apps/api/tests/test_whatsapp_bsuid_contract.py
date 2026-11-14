"""Meta wire contract: synthetic fixtures only; outbound HTTP is always mocked."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import ValidationError

from chatbot_api.core.settings import get_settings
from chatbot_api.schemas.whatsapp import ParsedInboundMessage, WhatsAppWebhookPayload
from chatbot_api.services import whatsapp_service
from chatbot_api.services.whatsapp_webhook_service import (
    extract_identity_changes,
    extract_messages,
    extract_statuses,
    resolve_identity_scope,
)

OPAQUE_ID = "PE.Aa00" + "X" * 124


@pytest.fixture(autouse=True)
def isolated_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://unused:unused@localhost/unused")
    monkeypatch.setenv("META_BUSINESS_PORTFOLIO_ID", "PORTFOLIO")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "SENDER")
    monkeypatch.setenv("META_ACCESS_TOKEN", "")
    get_settings.cache_clear()


def payload(
    messages: list[dict[str, Any]],
    contacts: list[dict[str, Any]] | None = None,
    **value_fields: Any,
) -> WhatsAppWebhookPayload:
    value: dict[str, Any] = {
        "metadata": {"phone_number_id": "SENDER"},
        "messages": messages,
        "contacts": contacts or [],
    }
    value.update(value_fields)
    return WhatsAppWebhookPayload.model_validate(
        {
            "entry": [{"id": "WABA_IS_NOT_PORTFOLIO", "changes": [{"value": value}]}],
        }
    )


def text(**fields: Any) -> dict[str, Any]:
    return {
        "id": "wamid.inbound",
        "timestamp": "1700000000",
        "type": "text",
        "text": {"body": "Hola"},
        **fields,
    }


@pytest.mark.parametrize("with_phone,with_bsuid", [(True, False), (False, True), (True, True)])
def test_phone_bsuid_and_combined_text(with_phone: bool, with_bsuid: bool) -> None:
    identity = {"from": "51900000001"} if with_phone else {}
    if with_bsuid:
        identity["from_user_id"] = OPAQUE_ID
    parsed = extract_messages(payload([text(**identity)]))[0]
    assert parsed.from_phone == ("+51900000001" if with_phone else None)
    assert parsed.from_user_id == (OPAQUE_ID if with_bsuid else None)
    assert parsed.identity_scope == "portfolio:PORTFOLIO"
    assert parsed.business_phone_number_id == "SENDER"
    assert parsed.text == "Hola"


def test_parent_username_and_contacts_match_per_message() -> None:
    parsed = extract_messages(
        payload(
            [
                text(from_user_id=OPAQUE_ID, from_parent_user_id="PE.ENT.Aa00"),
                text(**{"from": "51900000002"}),
            ],
            [
                {"wa_id": "51900000002", "profile": {"name": "Second"}},
                {"user_id": "PE.other", "profile": {"name": "Wrong"}},
                {
                    "user_id": OPAQUE_ID,
                    "parent_user_id": "PE.ENT.Aa00",
                    "profile": {"name": "First", "username": "first.user"},
                },
            ],
        )
    )
    assert [(msg.display_name, msg.from_phone) for msg in parsed] == [
        ("First", None),
        ("Second", "+51900000002"),
    ]
    assert parsed[0].username == "first.user"
    assert parsed[0].from_parent_user_id == "PE.ENT.Aa00"
    assert parsed[0].from_user_id == OPAQUE_ID


def test_legacy_phone_contact_can_supply_observed_bsuid_and_parent() -> None:
    parsed = extract_messages(
        payload(
            [text(**{"from": "51900000001"})],
            [
                {
                    "wa_id": "51900000001",
                    "user_id": OPAQUE_ID,
                    "parent_user_id": "PE.ENT.Parent",
                    "profile": {"username": "person"},
                }
            ],
        )
    )[0]
    assert parsed.from_user_id == OPAQUE_ID
    assert parsed.from_parent_user_id == "PE.ENT.Parent"
    assert parsed.username == "person"


def test_conflicting_or_unmatched_contacts_never_supply_metadata() -> None:
    parsed = extract_messages(
        payload(
            [text(**{"from": "51900000001", "from_user_id": OPAQUE_ID})],
            [
                {
                    "wa_id": "51900000001",
                    "user_id": "PE.other",
                    "profile": {"name": "Wrong", "username": "wrong"},
                },
                {
                    "wa_id": "51900000002",
                    "user_id": "PE.unrelated",
                    "profile": {"name": "Also wrong"},
                },
            ],
        )
    )[0]
    assert parsed.from_phone == "+51900000001"
    assert parsed.from_user_id == OPAQUE_ID
    assert parsed.display_name is None
    assert parsed.username is None


def test_exact_bsuid_match_wins_when_contact_wa_id_differs_from_actual_phone() -> None:
    parsed = extract_messages(
        payload(
            [text(**{"from": "51900000001", "from_user_id": OPAQUE_ID})],
            [
                {"wa_id": "51900000001", "profile": {"name": "Phone fallback"}},
                {
                    "wa_id": "51900000001",
                    "user_id": "PE.other",
                    "profile": {"name": "Wrong", "username": "wrong"},
                },
                {
                    "wa_id": "opaque.whatsapp.routing.id",
                    "user_id": OPAQUE_ID,
                    "parent_user_id": "PE.ENT.Parent",
                    "profile": {"name": "Correct", "username": "correct"},
                },
            ],
        )
    )[0]
    assert parsed.from_phone == "+51900000001"
    assert parsed.from_user_id == OPAQUE_ID
    assert parsed.display_name == "Correct"
    assert parsed.username == "correct"
    assert parsed.from_parent_user_id == "PE.ENT.Parent"


def test_bsuid_contact_wa_id_never_supplies_actual_phone() -> None:
    parsed = extract_messages(
        payload(
            [text(from_user_id=OPAQUE_ID)],
            [
                {
                    "wa_id": "opaque.whatsapp.routing.id",
                    "user_id": OPAQUE_ID,
                    "profile": {"name": "Correct"},
                }
            ],
        )
    )[0]
    assert parsed.from_phone is None
    assert parsed.display_name == "Correct"


def test_ambiguous_bsuid_contacts_do_not_fall_back_to_phone_metadata() -> None:
    parsed = extract_messages(
        payload(
            [text(**{"from": "51900000001", "from_user_id": OPAQUE_ID})],
            [
                {"user_id": OPAQUE_ID, "profile": {"name": "First"}},
                {"user_id": OPAQUE_ID, "profile": {"name": "Duplicate"}},
                {"wa_id": "51900000001", "profile": {"name": "Phone fallback"}},
            ],
        )
    )[0]
    assert parsed.display_name is None


def test_shared_vcard_does_not_link_phone() -> None:
    parsed = extract_messages(
        payload(
            [
                text(
                    from_user_id=OPAQUE_ID,
                    contacts=[{"phones": [{"wa_id": "51900000099"}]}],
                )
            ]
        )
    )[0]
    assert parsed.from_phone is None


@pytest.mark.parametrize("context", [{"forwarded": True}, {"frequently_forwarded": True}, {}])
def test_context_without_id_is_not_a_quote(context: dict[str, Any]) -> None:
    parsed = extract_messages(payload([text(from_user_id=OPAQUE_ID, context=context)]))[0]
    assert parsed.context_wamid is None


def test_quote_and_legacy_task_json_defaults() -> None:
    parsed = extract_messages(
        payload(
            [
                text(
                    **{
                        "from": "51900000001",
                        "context": {"id": "wamid.original"},
                    }
                )
            ]
        )
    )[0]
    assert parsed.context_wamid == "wamid.original"
    legacy = ParsedInboundMessage.model_validate(
        {
            "meta_message_id": "wamid.old",
            "from_phone": "+51900000001",
            "display_name": "Old task",
            "text": "Hola",
            "timestamp": "1700000000",
        }
    )
    assert legacy.from_user_id is None
    assert legacy.identity_scope is None
    assert legacy.business_phone_number_id is None


@pytest.mark.parametrize("identity", [{}, {"from": ""}, {"from_user_id": "  "}])
def test_text_requires_usable_identity(identity: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="requires from or from_user_id"):
        payload([text(**identity)])


def test_missing_text_body_is_rejected() -> None:
    message = text(from_user_id=OPAQUE_ID)
    message.pop("text")
    with pytest.raises(ValidationError, match=r"requires text\.body"):
        payload([message])


def test_failed_status_without_contacts_or_recipient() -> None:
    event = payload([], statuses=[{"id": "wamid.failed", "status": "failed"}])
    assert extract_messages(event) == []
    assert extract_identity_changes(event) == []
    assert extract_statuses(event)[0].model_dump() == {
        "meta_message_id": "wamid.failed",
        "status": "failed",
    }


@pytest.mark.parametrize("event_type", ["user_changed_user_id", "user_changed_number"])
def test_rotation_can_have_identity_only_inside_system(event_type: str) -> None:
    system = {
        "type": event_type,
        "user_id": OPAQUE_ID,
        "previous_user_id": "PE.Old",
        "parent_user_id": "PE.ENT.New",
        "previous_parent_user_id": "PE.ENT.Old",
    }
    message: dict[str, Any] = {
        "id": "wamid.rotation",
        "timestamp": "1700000000",
        "type": "system",
        "system": system,
    }
    if event_type == "user_changed_number":
        message["from"] = "51900000001"
        system["wa_id"] = "opaque.whatsapp.routing.id.Aa00"
    event = payload([message])
    assert extract_messages(event) == []
    change = extract_identity_changes(event)[0]
    assert change.system_type == event_type
    assert change.user_id == OPAQUE_ID
    assert change.previous_user_id == "PE.Old"
    assert change.parent_user_id == "PE.ENT.New"
    assert change.previous_parent_user_id == "PE.ENT.Old"
    assert change.identity_scope == "portfolio:PORTFOLIO"
    assert change.business_phone_number_id == "SENDER"
    assert change.new_wa_id == ("opaque.whatsapp.routing.id.Aa00" if "from" in message else None)
    assert "new_phone" not in change.model_dump()
    assert change.from_phone == ("+51900000001" if "from" in message else None)


@pytest.mark.parametrize("event_type", ["user_changed_user_id", "user_changed_number"])
def test_rotation_validates_identity_for_event_type(event_type: str) -> None:
    with pytest.raises(ValidationError, match="requires system"):
        payload(
            [
                {
                    "id": "wamid.bad",
                    "timestamp": "1",
                    "type": "system",
                    "system": {"type": event_type},
                }
            ]
        )


def test_phone_only_rotation_and_optional_previous_ids_remain_valid() -> None:
    event = payload(
        [
            {
                "id": "wamid.phone",
                "timestamp": "1",
                "type": "system",
                "from": "51900000001",
                "system": {"type": "user_changed_number", "wa_id": "51900000002"},
            }
        ]
    )
    change = extract_identity_changes(event)[0]
    assert change.user_id is None
    assert change.previous_user_id is None
    assert change.new_wa_id == "51900000002"
    assert change.from_phone == "+51900000001"
    assert "new_phone" not in change.model_dump()


def test_unknown_system_type_does_not_become_text_or_block_other_text() -> None:
    event = payload(
        [
            {
                "id": "wamid.future",
                "timestamp": "1",
                "type": "system",
                "system": {"type": "future_notification"},
            },
            text(from_user_id=OPAQUE_ID),
        ]
    )
    assert len(extract_messages(event)) == 1
    assert extract_identity_changes(event) == []


def test_scope_uses_portfolio_then_authoritative_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    assert resolve_identity_scope(business_phone_number_id="OTHER") == "portfolio:PORTFOLIO"
    monkeypatch.setenv("META_BUSINESS_PORTFOLIO_ID", "")
    get_settings.cache_clear()
    assert resolve_identity_scope(business_phone_number_id="OTHER") == "sender:OTHER"
    assert resolve_identity_scope() == "sender:SENDER"
    parsed = extract_messages(payload([text(from_user_id=OPAQUE_ID)], metadata=None))[0]
    assert parsed.identity_scope == "sender:SENDER"
    assert parsed.business_phone_number_id == "SENDER"
    parsed = extract_messages(
        payload(
            [text(from_user_id=OPAQUE_ID)],
            metadata={"phone_number_id": "OTHER"},
        )
    )[0]
    assert parsed.identity_scope == "sender:OTHER"
    assert parsed.business_phone_number_id == "OTHER"


def test_unscoped_bsuid_is_explicitly_rejected_but_legacy_phone_is_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("META_BUSINESS_PORTFOLIO_ID", "")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="requires a business portfolio or sender scope"):
        extract_messages(payload([text(from_user_id=OPAQUE_ID)], metadata=None))
    parsed = extract_messages(payload([text(**{"from": "51900000001"})], metadata=None))[0]
    assert parsed.from_phone == "+51900000001"
    assert parsed.identity_scope is None


def test_present_metadata_without_sender_never_falls_back_to_configured_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("META_BUSINESS_PORTFOLIO_ID", "")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="requires a business portfolio or sender scope"):
        extract_messages(payload([text(from_user_id=OPAQUE_ID)], metadata={}))


@pytest.mark.parametrize(
    "recipients",
    [
        {},
        {"to": "+51900000001", "recipient": OPAQUE_ID},
        {"to": ""},
        {"recipient": "  "},
        {"to": "", "recipient": OPAQUE_ID},
    ],
)
async def test_outbound_rejects_missing_dual_or_empty_before_dev_bypass(
    recipients: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_factory = MagicMock()
    monkeypatch.setattr(whatsapp_service, "_get_client", client_factory)
    with pytest.raises(ValueError):
        await whatsapp_service.send_message(**recipients, body="Hola")
    client_factory.assert_not_called()


@pytest.mark.parametrize("mode,destination", [("to", "+51900000001"), ("recipient", OPAQUE_ID)])
@pytest.mark.parametrize("context", [None, {"message_id": "wamid.quoted"}])
async def test_exact_outbound_json_and_client_close(
    mode: str,
    destination: str,
    context: dict[str, str] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "synthetic-test-token")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v21.0")
    get_settings.cache_clear()
    url = "https://graph.facebook.com/v21.0/SENDER/messages"
    response = httpx.Response(
        200, json={"messages": [{"id": "wamid.sent"}]}, request=httpx.Request("POST", url)
    )
    client = MagicMock(post=AsyncMock(return_value=response), aclose=AsyncMock())
    monkeypatch.setattr(whatsapp_service, "_get_client", lambda: client)
    result = await whatsapp_service.send_message(
        **{mode: destination}, body="Hola", context=context
    )
    expected: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "text",
        "text": {"body": "Hola"},
        mode: destination.lstrip("+") if mode == "to" else destination,
    }
    if context:
        expected["context"] = context
    assert result == "wamid.sent"
    client.post.assert_awaited_once_with(
        url,
        json=expected,
        headers={
            "Authorization": "Bearer synthetic-test-token",
            "Content-Type": "application/json",
        },
    )
    client.aclose.assert_awaited_once()


@pytest.mark.parametrize("response_json", [{}, {"messages": []}, {"messages": [{}]}])
async def test_outbound_requires_wamid_and_closes_client(
    response_json: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "synthetic-test-token")
    get_settings.cache_clear()
    response = httpx.Response(
        200, json=response_json, request=httpx.Request("POST", "https://example.test/messages")
    )
    client = MagicMock(post=AsyncMock(return_value=response), aclose=AsyncMock())
    monkeypatch.setattr(whatsapp_service, "_get_client", lambda: client)
    with pytest.raises(RuntimeError, match="meta response missing"):
        await whatsapp_service.send_message(recipient=OPAQUE_ID, body="Hola")
    client.aclose.assert_awaited_once()


async def test_outbound_http_error_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "synthetic-test-token")
    get_settings.cache_clear()
    response = httpx.Response(400, request=httpx.Request("POST", "https://example.test/messages"))
    client = MagicMock(post=AsyncMock(return_value=response), aclose=AsyncMock())
    monkeypatch.setattr(whatsapp_service, "_get_client", lambda: client)
    with pytest.raises(httpx.HTTPStatusError):
        await whatsapp_service.send_message(recipient=OPAQUE_ID, body="Hola")
    client.aclose.assert_awaited_once()


async def test_bsuid_dev_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    client_factory = MagicMock()
    monkeypatch.setattr(whatsapp_service, "_get_client", client_factory)
    assert (await whatsapp_service.send_message(recipient=OPAQUE_ID, body="Hola")).startswith(
        "wamid.dev.",
    )
    client_factory.assert_not_called()


@pytest.mark.parametrize("typing", [False, True])
async def test_mark_read_contract_still_uses_wamid_and_closes_client(
    typing: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "synthetic-test-token")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v21.0")
    get_settings.cache_clear()
    url = "https://graph.facebook.com/v21.0/SENDER/messages"
    response = httpx.Response(200, request=httpx.Request("POST", url))
    client = MagicMock(post=AsyncMock(return_value=response), aclose=AsyncMock())
    monkeypatch.setattr(whatsapp_service, "_get_client", lambda: client)
    await whatsapp_service.mark_read(message_id="wamid.inbound", typing=typing)
    expected: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": "wamid.inbound",
    }
    if typing:
        expected["typing_indicator"] = {"type": "text"}
    assert client.post.await_args.kwargs["json"] == expected
    client.aclose.assert_awaited_once()


def test_empty_optional_phone_never_becomes_plus() -> None:
    parsed = extract_messages(payload([text(**{"from": "  ", "from_user_id": OPAQUE_ID})]))[0]
    assert parsed.from_phone is None
    assert parsed.from_user_id == OPAQUE_ID


def test_blank_contact_identifiers_are_absent() -> None:
    parsed = extract_messages(
        payload(
            [text(**{"from": "51900000001"})],
            [{"wa_id": "51900000001", "user_id": "  ", "parent_user_id": ""}],
        )
    )[0]
    assert parsed.from_user_id is None
    assert parsed.from_parent_user_id is None
