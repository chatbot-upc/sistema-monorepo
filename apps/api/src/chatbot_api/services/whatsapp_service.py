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


async def send_message(*, to: str, body: str) -> str:
    """POST a text message to Meta Cloud API. Returns the `wamid` echoed back.

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
