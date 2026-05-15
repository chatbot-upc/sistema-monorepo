"""WhatsApp webhook helpers: HMAC validation + payload normalization.

Module-level functions (RORO). No shared state — the outbound httpx client lives in
`whatsapp_service.py` (Fase 4).
"""

from __future__ import annotations

import hashlib
import hmac

from chatbot_api.schemas.whatsapp import (
    ParsedInboundMessage,
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


def extract_messages(payload: WhatsAppWebhookPayload) -> list[ParsedInboundMessage]:
    """Walk entry[].changes[].value.messages[] and emit flat ParsedInboundMessage objects.

    Non-text messages (image, audio, status receipts, etc.) are skipped — we only handle
    text inbound for SW-13. The display_name is resolved from contacts[] by wa_id.
    """
    parsed: list[ParsedInboundMessage] = []
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            contacts_by_wa_id = {c.wa_id: c for c in value.contacts}
            for msg in value.messages:
                if msg.type != "text" or msg.text is None:
                    continue
                contact = contacts_by_wa_id.get(msg.from_phone)
                display_name = contact.profile.name if contact and contact.profile else None
                parsed.append(
                    ParsedInboundMessage(
                        meta_message_id=msg.id,
                        from_phone=_normalize_phone(msg.from_phone),
                        display_name=display_name,
                        text=msg.text.body,
                        timestamp=msg.timestamp,
                    )
                )
    return parsed


def _normalize_phone(raw: str) -> str:
    """Meta strips the leading '+'; we re-prepend it for E.164 storage."""
    raw = raw.strip()
    if not raw.startswith("+"):
        return f"+{raw}"
    return raw
