"""Outbound WhatsApp via Meta Cloud API (Graph API).

Each call builds its own `httpx.AsyncClient`. Celery workers run every task
inside a separate `asyncio.run()` — a process-wide client would end up tied
to a dead event loop on the second task and crash with "Event loop is closed".
The cost of one TLS handshake per call (~30-50 ms) is negligible next to the
~5-10s of RAG round-trips. The `_get_client` factory stays as a seam for
test mocking via `monkeypatch.setattr`.

Dev-bypass: when META_ACCESS_TOKEN is unset, `send_message` logs the outbound
and returns a synthetic id instead of hitting Meta.
"""

from __future__ import annotations

import secrets
from typing import Any

import httpx
import structlog

from chatbot_api.core.settings import get_settings

log = structlog.get_logger()

_DEV_PREFIX = "wamid.dev."
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _get_client() -> httpx.AsyncClient:
    """Builds a fresh client per call (see module docstring)."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


async def shutdown() -> None:
    """Kept for the FastAPI lifespan interface — no shared state to release."""
    return None


def _normalize_to(phone: str) -> str:
    """Meta expects E.164 without leading '+'."""
    return phone[1:] if phone.startswith("+") else phone


async def send_message(
    *, to: str, body: str, context: dict[str, Any] | None = None
) -> str:
    """POST a text message to Meta Cloud API. Returns the `wamid` echoed back.

    `context={"message_id": wamid}` cita (responde a) un mensaje previo — la cita
    nativa de WhatsApp. Si es None, la clave se omite del payload (mismo efecto que
    el `.compact` de Chatwoot): el método sirve para mensajes normales y respuestas.

    Raises `httpx.HTTPStatusError` on Meta-side errors (the worker retries via Celery).
    """
    settings = get_settings()
    if not settings.meta_access_token or not settings.meta_phone_number_id:
        synthetic = f"{_DEV_PREFIX}{secrets.token_hex(8)}"
        log.warning(
            "whatsapp_outbound_dev_bypass",
            to=to,
            body_preview=body[:80],
            synthetic_id=synthetic,
            in_reply_to=context.get("message_id") if context else None,
        )
        return synthetic

    url = (
        f"https://graph.facebook.com/{settings.meta_graph_api_version}/"
        f"{settings.meta_phone_number_id}/messages"
    )
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": _normalize_to(to),
        "type": "text",
        "text": {"body": body},
    }
    if context:
        payload["context"] = context
    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }
    client = _get_client()
    try:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    finally:
        await client.aclose()
    messages = data.get("messages") or []
    if not messages:
        raise RuntimeError(f"meta response missing messages[]: {data}")
    meta_id = messages[0].get("id")
    if not isinstance(meta_id, str):
        raise RuntimeError(f"meta response missing message id: {data}")
    log.info("whatsapp_outbound_sent", to=to, meta_message_id=meta_id)
    return meta_id


async def mark_read(*, message_id: str, typing: bool = False) -> None:
    """Marca un mensaje entrante como leído (✓✓ azul) y, si typing=True, muestra
    el indicador "escribiendo…" al estudiante.

    Mismo endpoint que el envío: Meta combina el acuse de lectura y el typing en
    un POST con `status:read`. El indicador se descarta al enviar el siguiente
    mensaje o a los ~25s. Best-effort: cualquier fallo se loguea y NO se propaga
    (un acuse perdido no debe romper el pipeline de conversación).
    """
    settings = get_settings()
    # Dev-bypass o ids sintéticos (no existen en Meta) → no-op.
    if (
        not settings.meta_access_token
        or not settings.meta_phone_number_id
        or message_id.startswith(_DEV_PREFIX)
    ):
        log.info("whatsapp_mark_read_skipped", message_id=message_id, typing=typing)
        return

    url = (
        f"https://graph.facebook.com/{settings.meta_graph_api_version}/"
        f"{settings.meta_phone_number_id}/messages"
    )
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    if typing:
        payload["typing_indicator"] = {"type": "text"}
    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }
    client = _get_client()
    try:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        log.info("whatsapp_mark_read_sent", message_id=message_id, typing=typing)
    except Exception:
        log.warning(
            "whatsapp_mark_read_failed", message_id=message_id, typing=typing
        )
    finally:
        await client.aclose()
