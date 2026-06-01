"""SW-26 — Redis 24h cache para historial con fallback a Postgres."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Message
from chatbot_api.models.enums import MessageRole
from chatbot_api.services import conversation_history_service

from . import factories


def _key(conv_id: int) -> str:
    return f"chatbot:history:{conv_id}"


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> fakeredis.aioredis.FakeRedis:
    """Reactiva el cache (off por defecto en conftest) y monkeypatchea Redis."""
    monkeypatch.setenv("HISTORY_CACHE_ENABLED", "true")
    get_settings.cache_clear()
    client = fakeredis.aioredis.FakeRedis(decode_responses=False)

    def _from_url(*_args: Any, **_kwargs: Any) -> Any:
        return client

    monkeypatch.setattr(
        "chatbot_api.services.conversation_history_service.Redis.from_url",
        _from_url,
    )
    return client


@pytest.fixture
def reset_settings_cache() -> None:
    get_settings.cache_clear()


async def _seed_conv_with_messages(
    db: AsyncSession, *, phone: str, count: int
) -> tuple[int, list[Message]]:
    student = await factories.make_student(db, phone=phone)
    conv = await factories.make_conversation(db, student_phone=student.phone_e164)
    msgs: list[Message] = []
    for i in range(count):
        role = MessageRole.student if i % 2 == 0 else MessageRole.bot
        msg = await factories.make_message(
            db, conversation_id=conv.id, role=role, content=f"msg-{i}"
        )
        msgs.append(msg)
    await db.flush()
    return conv.id, msgs


# ---------- 1. Cache hit ----------------------------------------------------


async def test_cache_hit_skips_db(
    fake_redis: Any,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conv_id, _ = await _seed_conv_with_messages(
        db_session, phone="+51900260001", count=2
    )

    # Pre-poblar Redis manualmente con 2 entries
    pre = [
        json.dumps({"role": "user", "content": "hola"}),
        json.dumps({"role": "assistant", "content": "hola back"}),
    ]
    await fake_redis.rpush(_key(conv_id), *pre)
    await fake_redis.expire(_key(conv_id), 86400)

    # Spy en el método del repo para verificar que NO se llama
    spy = AsyncMock(
        wraps=conversation_history_service.message_repository.list_recent_for_conversation
    )
    monkeypatch.setattr(
        conversation_history_service.message_repository,
        "list_recent_for_conversation",
        spy,
    )

    history = await conversation_history_service.get(
        db_session, conversation_id=conv_id
    )
    assert history == [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola back"},
    ]
    spy.assert_not_called()


# ---------- 2. Cache miss → DB + populate -----------------------------------


async def test_cache_miss_loads_from_db_and_populates(
    fake_redis: Any, db_session: AsyncSession
) -> None:
    conv_id, _ = await _seed_conv_with_messages(
        db_session, phone="+51900260002", count=3
    )

    # Cache vacío
    assert await fake_redis.exists(_key(conv_id)) == 0

    history = await conversation_history_service.get(
        db_session, conversation_id=conv_id
    )
    assert len(history) == 3
    assert all(h["content"].startswith("msg-") for h in history)

    # Después del get, el cache debe quedar poblado
    cached_len = await fake_redis.llen(_key(conv_id))
    assert cached_len == 3
    ttl = await fake_redis.ttl(_key(conv_id))
    assert ttl > 0


# ---------- 3. Append push + trim + expire ----------------------------------


async def test_append_pushes_and_trims_and_sets_ttl(
    fake_redis: Any, db_session: AsyncSession
) -> None:
    conv_id, msgs = await _seed_conv_with_messages(
        db_session, phone="+51900260003", count=2
    )

    await conversation_history_service.append(
        conversation_id=conv_id, messages=msgs
    )

    cached_len = await fake_redis.llen(_key(conv_id))
    assert cached_len == 2
    ttl = await fake_redis.ttl(_key(conv_id))
    assert 86000 < ttl <= 86400


# ---------- 4. Sliding window (LTRIM) ---------------------------------------


async def test_append_sliding_window(
    fake_redis: Any, db_session: AsyncSession
) -> None:
    conv_id, _ = await _seed_conv_with_messages(
        db_session, phone="+51900260004", count=0
    )

    # Pre-poblar Redis con 25 entries dummy (simula historial grande)
    for i in range(25):
        await fake_redis.rpush(
            _key(conv_id),
            json.dumps({"role": "user", "content": f"old-{i}"}),
        )

    new_msg = await factories.make_message(
        db_session,
        conversation_id=conv_id,
        role=MessageRole.bot,
        content="brand-new",
    )

    await conversation_history_service.append(
        conversation_id=conv_id, messages=[new_msg]
    )

    cached_len = await fake_redis.llen(_key(conv_id))
    # max_messages = 20 (default), LTRIM mantiene los últimos 20
    assert cached_len == 20
    # El último elemento debe ser el nuevo
    last = await fake_redis.lrange(_key(conv_id), -1, -1)
    assert json.loads(last[0])["content"] == "brand-new"


# ---------- 5. Append refresca TTL ------------------------------------------


async def test_append_refreshes_ttl(
    fake_redis: Any, db_session: AsyncSession
) -> None:
    conv_id, _ = await _seed_conv_with_messages(
        db_session, phone="+51900260005", count=0
    )

    # Poner una key con TTL bajo
    await fake_redis.rpush(
        _key(conv_id),
        json.dumps({"role": "user", "content": "viejo"}),
    )
    await fake_redis.expire(_key(conv_id), 10)
    pre_ttl = await fake_redis.ttl(_key(conv_id))
    assert pre_ttl <= 10

    new_msg = await factories.make_message(
        db_session, conversation_id=conv_id, content="fresco"
    )
    await conversation_history_service.append(
        conversation_id=conv_id, messages=[new_msg]
    )

    post_ttl = await fake_redis.ttl(_key(conv_id))
    assert post_ttl > pre_ttl
    assert post_ttl > 80000  # ~86400 default


# ---------- 6. Redis caído → fallback DB transparente -----------------------


async def test_redis_down_falls_back_to_db(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HISTORY_CACHE_ENABLED", "true")
    get_settings.cache_clear()
    conv_id, _ = await _seed_conv_with_messages(
        db_session, phone="+51900260006", count=2
    )

    def _broken(*_args: Any, **_kwargs: Any) -> Any:
        raise ConnectionError("redis down (simulated)")

    monkeypatch.setattr(
        "chatbot_api.services.conversation_history_service.Redis.from_url",
        _broken,
    )

    # get debe seguir devolviendo data desde DB sin levantar
    history = await conversation_history_service.get(
        db_session, conversation_id=conv_id
    )
    assert len(history) == 2

    # append no debe levantar tampoco
    msgs = await conversation_history_service._load_from_db(
        db_session,
        conversation_id=conv_id,
        exclude_message_id=None,
        ttl_seconds=86400,
        max_messages=20,
    )
    await conversation_history_service.append(
        conversation_id=conv_id, messages=msgs
    )
