"""Cache de historial conversacional en Redis con fallback a DB (SW-26).

Patrón cache-aside con append-on-write:
- `get`: trata Redis primero (LRANGE), si miss → DB → poblar Redis.
- `append`: pipeline RPUSH + LTRIM + EXPIRE (sliding 24h TTL).
- Cualquier fallo de Redis se loguea pero **no se propaga** — la conversación
  nunca se rompe por Redis caído, simplemente cae a DB.

Key shape: `chatbot:history:{conversation_id}`. Granularidad por conv
(no por phone) porque cada conv es un "caso de atención" independiente.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Message
from chatbot_api.models.enums import MessageRole
from chatbot_api.repositories.message import message_repository

log = structlog.get_logger()

_KEY_PREFIX = "chatbot:history:"


def _key(conv_id: int) -> str:
    return f"{_KEY_PREFIX}{conv_id}"


def _serialize(msg: Message) -> str | None:
    """Serializa Message al shape LangChain. None si no es cacheable."""
    if not msg.content:
        return None
    role = "user" if msg.role == MessageRole.student else "assistant"
    return json.dumps({"role": role, "content": msg.content})


async def _load_from_db(
    db: AsyncSession,
    *,
    conversation_id: int,
    exclude_message_id: int | None,
    ttl_seconds: int,
    max_messages: int,
) -> list[Message]:
    since = datetime.now() - timedelta(seconds=ttl_seconds)
    return await message_repository.list_recent_for_conversation(
        db,
        conversation_id=conversation_id,
        since=since,
        exclude_after_id=exclude_message_id,
        limit=max_messages,
    )


def _messages_to_history(messages: list[Message]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for m in messages:
        if not m.content:
            continue
        role = "user" if m.role == MessageRole.student else "assistant"
        history.append({"role": role, "content": m.content})
    return history


async def _try_read_cache(conv_id: int) -> list[dict[str, str]] | None:
    """LRANGE. None si key no existe; lista (posiblemente vacía) si existe."""
    settings = get_settings()
    try:
        client: Any = Redis.from_url(settings.redis_url)
        try:
            exists = await client.exists(_key(conv_id))
            if not exists:
                return None
            raw = await client.lrange(_key(conv_id), 0, -1)
        finally:
            await client.aclose()
    except Exception:
        log.exception("history_cache_read_failed", conv_id=conv_id)
        return None

    history: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, bytes):
            item = item.decode("utf-8")
        try:
            parsed = json.loads(item)
            if isinstance(parsed, dict) and "role" in parsed and "content" in parsed:
                history.append({"role": parsed["role"], "content": parsed["content"]})
        except (json.JSONDecodeError, TypeError):
            continue
    return history


async def _populate_cache(conv_id: int, messages: list[Message]) -> None:
    """DEL + RPUSH (N veces) + LTRIM + EXPIRE en pipeline. Errores no propagan."""
    settings = get_settings()
    entries = [s for s in (_serialize(m) for m in messages) if s is not None]
    if not entries:
        return
    try:
        client: Any = Redis.from_url(settings.redis_url)
        try:
            pipe = client.pipeline(transaction=False)
            pipe.delete(_key(conv_id))
            for entry in entries:
                pipe.rpush(_key(conv_id), entry)
            pipe.ltrim(
                _key(conv_id), -settings.history_cache_max_messages, -1
            )
            pipe.expire(_key(conv_id), settings.history_cache_ttl_seconds)
            await pipe.execute()
        finally:
            await client.aclose()
    except Exception:
        log.exception("history_cache_populate_failed", conv_id=conv_id)


async def get(
    db: AsyncSession,
    *,
    conversation_id: int,
    exclude_message_id: int | None = None,
) -> list[dict[str, str]]:
    """Historial reciente en formato LangChain.

    - Si cache habilitado y existe: devuelve del cache.
    - Si cache miss: lee DB con `exclude_message_id` (excluye el inbound del
      turno actual si aplica) y puebla el cache con esa data.
    - Si Redis falla en cualquier punto: fallback total a DB sin propagar.
    """
    settings = get_settings()
    if not settings.history_cache_enabled:
        msgs = await _load_from_db(
            db,
            conversation_id=conversation_id,
            exclude_message_id=exclude_message_id,
            ttl_seconds=settings.history_cache_ttl_seconds,
            max_messages=settings.history_cache_max_messages,
        )
        return _messages_to_history(msgs)

    cached = await _try_read_cache(conversation_id)
    if cached is not None:
        log.debug(
            "history_cache_hit", conversation_id=conversation_id, turns=len(cached)
        )
        return cached

    msgs = await _load_from_db(
        db,
        conversation_id=conversation_id,
        exclude_message_id=exclude_message_id,
        ttl_seconds=settings.history_cache_ttl_seconds,
        max_messages=settings.history_cache_max_messages,
    )
    if msgs:
        await _populate_cache(conversation_id, msgs)
    log.debug(
        "history_cache_miss", conversation_id=conversation_id, turns=len(msgs)
    )
    return _messages_to_history(msgs)


async def append(conversation_id: int, messages: list[Message]) -> None:
    """Append best-effort. Refresca TTL (sliding window). Errores no propagan."""
    settings = get_settings()
    if not settings.history_cache_enabled or not messages:
        return
    entries = [s for s in (_serialize(m) for m in messages) if s is not None]
    if not entries:
        return
    try:
        client: Any = Redis.from_url(settings.redis_url)
        try:
            pipe = client.pipeline(transaction=False)
            for entry in entries:
                pipe.rpush(_key(conversation_id), entry)
            pipe.ltrim(
                _key(conversation_id),
                -settings.history_cache_max_messages,
                -1,
            )
            pipe.expire(
                _key(conversation_id), settings.history_cache_ttl_seconds
            )
            await pipe.execute()
        finally:
            await client.aclose()
    except Exception:
        log.exception(
            "history_cache_append_failed", conversation_id=conversation_id
        )


async def clear(conversation_id: int) -> None:
    """Borra la key. Útil para reopen u operaciones admin puntuales."""
    settings = get_settings()
    if not settings.history_cache_enabled:
        return
    try:
        client: Any = Redis.from_url(settings.redis_url)
        try:
            await client.delete(_key(conversation_id))
        finally:
            await client.aclose()
    except Exception:
        log.exception(
            "history_cache_clear_failed", conversation_id=conversation_id
        )
