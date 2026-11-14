"""WhatsApp webhook helpers: HMAC validation + payload normalization.

Module-level functions (RORO). No shared state — the outbound httpx client lives in
`whatsapp_service.py` (Fase 4).
"""

from __future__ import annotations

import hashlib
import hmac

from chatbot_api.core.settings import get_settings
from chatbot_api.schemas.whatsapp import (
    ParsedIdentityChange,
    ParsedInboundMessage,
    ParsedStatus,
    WhatsAppContact,
    WhatsAppMessage,
    WhatsAppWebhookPayload,
)

_SIGNATURE_PREFIX = "sha256="


def verify_signature(*, raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Validate Meta's `X-Hub-Signature-256` header against `app_secret`.

    Returns False on any malformed input. We never raise — caller decides the HTTP code.
    """
    if not app_secret or not signature_header:
        return False
    if not signature_header.startswith(_SIGNATURE_PREFIX):
        return False
    provided = signature_header[len(_SIGNATURE_PREFIX) :]
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


def resolve_identity_scope(*, business_phone_number_id: str | None = None) -> str | None:
    """Namespace BSUIDs by portfolio; sender-only fallback isolates unconfigured installs.

    Configure META_BUSINESS_PORTFOLIO_ID before rollout: sender namespaces cannot
    establish continuity across different senders in the same portfolio. Never use
    entry.id (WABA ID) as a portfolio. An explicitly empty sender disables fallback.
    """
    settings = get_settings()
    if settings.meta_business_portfolio_id.strip():
        return f"portfolio:{settings.meta_business_portfolio_id.strip()}"
    sender = (
        settings.meta_phone_number_id
        if business_phone_number_id is None
        else business_phone_number_id
    )
    return f"sender:{sender}" if sender and sender.strip() else None


def _matching_contact(
    msg: WhatsAppMessage, contacts: list[WhatsAppContact]
) -> WhatsAppContact | None:
    """Match identifiers, never array position, names, or nested shared vCards."""
    user_matches = []
    phone_matches = []
    for contact in contacts:
        if msg.from_user_id and contact.user_id and msg.from_user_id != contact.user_id:
            continue
        if msg.from_user_id and msg.from_user_id == contact.user_id:
            # Meta's contact wa_id can differ from the actual message phone.
            user_matches.append(contact)
        elif (
            msg.from_phone
            and contact.wa_id
            and _normalize_phone(msg.from_phone) == _normalize_phone(contact.wa_id)
        ):
            phone_matches.append(contact)
    matches = user_matches or phone_matches
    return matches[0] if len(matches) == 1 else None


def extract_messages(payload: WhatsAppWebhookPayload) -> list[ParsedInboundMessage]:
    """Walk entry[].changes[].value.messages[] and emit flat ParsedInboundMessage objects.

    Non-text messages (image, audio, status receipts, etc.) are skipped — we only handle
    text inbound. Profile metadata is matched by user ID or phone for each message.
    """
    parsed: list[ParsedInboundMessage] = []
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            sender = (
                value.metadata.phone_number_id or ""
                if value.metadata
                else get_settings().meta_phone_number_id
            )
            scope = resolve_identity_scope(business_phone_number_id=sender)
            for msg in value.messages:
                if msg.type != "text" or msg.text is None:
                    continue
                contact = _matching_contact(msg, value.contacts)
                display_name = contact.profile.name if contact and contact.profile else None
                user_id = msg.from_user_id or (contact.user_id if contact else None)
                if user_id and not scope:
                    raise ValueError("BSUID text requires a business portfolio or sender scope")
                parsed.append(
                    ParsedInboundMessage(
                        meta_message_id=msg.id,
                        from_phone=_normalize_phone(msg.from_phone) if msg.from_phone else None,
                        from_user_id=user_id,
                        from_parent_user_id=(
                            msg.from_parent_user_id or (contact.parent_user_id if contact else None)
                        ),
                        username=contact.profile.username if contact and contact.profile else None,
                        identity_scope=scope,
                        business_phone_number_id=sender or None,
                        display_name=display_name,
                        text=msg.text.body,
                        timestamp=msg.timestamp,
                        context_wamid=msg.context.id if msg.context else None,
                    )
                )
    return parsed


def extract_identity_changes(payload: WhatsAppWebhookPayload) -> list[ParsedIdentityChange]:
    """Flatten official system events; identities may exist only inside system."""
    parsed = []
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            sender = (
                value.metadata.phone_number_id or ""
                if value.metadata
                else get_settings().meta_phone_number_id
            )
            scope = resolve_identity_scope(business_phone_number_id=sender)
            for msg in value.messages:
                system = msg.system
                if msg.type != "system" or system is None:
                    continue
                if system.type not in ("user_changed_number", "user_changed_user_id"):
                    continue
                if (system.user_id or system.previous_user_id) and not scope:
                    raise ValueError(
                        "BSUID system event requires a business portfolio or sender scope"
                    )
                parsed.append(
                    ParsedIdentityChange(
                        meta_message_id=msg.id,
                        timestamp=msg.timestamp,
                        system_type=system.type,
                        identity_scope=scope,
                        business_phone_number_id=sender or None,
                        user_id=system.user_id,
                        previous_user_id=system.previous_user_id,
                        from_phone=_normalize_phone(msg.from_phone) if msg.from_phone else None,
                        new_wa_id=system.wa_id,
                        parent_user_id=system.parent_user_id,
                        previous_parent_user_id=system.previous_parent_user_id,
                    )
                )
    return parsed


def extract_statuses(payload: WhatsAppWebhookPayload) -> list[ParsedStatus]:
    """Recolecta los acuses de entrega (value.statuses[]) de mensajes salientes.

    Cada uno referencia por wamid (= meta_message_id de nuestro mensaje) y trae
    el nuevo estado (sent/delivered/read/failed).
    """
    parsed: list[ParsedStatus] = []
    for entry in payload.entry:
        for change in entry.changes:
            for st in change.value.statuses:
                parsed.append(ParsedStatus(meta_message_id=st.id, status=st.status))
    return parsed


def _normalize_phone(raw: str) -> str:
    """Meta strips the leading '+'; we re-prepend it for E.164 storage."""
    raw = raw.strip()
    if not raw.startswith("+"):
        return f"+{raw}"
    return raw
