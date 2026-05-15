"""Outbound WhatsApp via Meta Cloud API (Graph API).

Module-level `_client` httpx.AsyncClient — Python guarantees the module is initialized
once per process. Worker procs build their own client; the FastAPI lifespan closes it
for the API process (see `core/lifespan.py`).

Dev-bypass: when META_ACCESS_TOKEN is unset, `send_message` logs the outbound and
returns a synthetic id instead of hitting Meta. Keeps local dev unblocked without
real Meta sandbox credentials.
"""

from __future__ import annotations

import secrets
from typing import Any

import httpx
import structlog

from chatbot_api.core.settings import get_settings

log = structlog.get_logger()

_client: httpx.AsyncClient | None = None
_DEV_PREFIX = "wamid.dev."


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    return _client


async def shutdown() -> None:
    """Close the shared client. Invoked from the FastAPI lifespan."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


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
    resp = await _get_client().post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    messages = data.get("messages") or []
    if not messages:
        raise RuntimeError(f"meta response missing messages[]: {data}")
    meta_id = messages[0].get("id")
    if not isinstance(meta_id, str):
        raise RuntimeError(f"meta response missing message id: {data}")
    log.info("whatsapp_outbound_sent", to=to, meta_message_id=meta_id)
    return meta_id
