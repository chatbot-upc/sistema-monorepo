"""SW-28 HU19 tests — internal monitoring endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.timezone import LOCAL_UTC_OFFSET, today_local_start
from chatbot_api.models import Conversation, Message
from chatbot_api.models.enums import ConversationStatus, MessageRole
from tests.factories import make_conversation, make_student

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


async def _seed_messages(db: AsyncSession) -> Conversation:
    await make_student(db, phone="+51900028001", display_name="Monitor Test")
    conv = await make_conversation(db, student_phone="+51900028001")

    now = datetime.now()
    # created_at se guarda como UTC naive; "hoy" se mide en hora de Lima
    # (to_local). Cerca de la medianoche de Lima, "hace 5-30 min" caería en el
    # día anterior y los tokens/conversaciones de hoy darían 0 → flaky. Acotamos
    # el timestamp para que nunca cruce la medianoche de Lima; sigue dentro de la
    # última hora porque, de aplicarse el tope, estaríamos a <1h de medianoche.
    today_utc_floor = today_local_start() - LOCAL_UTC_OFFSET + timedelta(minutes=1)
    rows: list[dict[str, Any]] = [
        # 3 inbound messages last hour (2 SBERT, 1 fallback)
        {"role": MessageRole.student, "delta": timedelta(minutes=5), "fallback": False},
        {"role": MessageRole.student, "delta": timedelta(minutes=15), "fallback": False},
        {"role": MessageRole.student, "delta": timedelta(minutes=30), "fallback": True},
        # 2 bot replies with latency
        {
            "role": MessageRole.bot,
            "delta": timedelta(minutes=5),
            "latency_ms": 2000,
            "input_tokens": 100,
            "output_tokens": 50,
        },
        {
            "role": MessageRole.bot,
            "delta": timedelta(minutes=15),
            "latency_ms": 6000,
            "input_tokens": 80,
            "output_tokens": 40,
        },
    ]
    for i, r in enumerate(rows):
        msg = Message(
            conversation_id=conv.id,
            role=r["role"],
            content=f"msg-{i}",
            retrieved_chunks=[],
            created_at=max(now - r["delta"], today_utc_floor),
            intent_used_fallback=r.get("fallback")
            if r["role"] == MessageRole.student
            else None,
            latency_ms=r.get("latency_ms"),
            input_tokens=r.get("input_tokens"),
            output_tokens=r.get("output_tokens"),
        )
        db.add(msg)
    await db.flush()
    return conv


async def _fetch_health(client: AsyncClient, *, queue: int, workers: int) -> dict:
    with (
        patch(
            "chatbot_api.services.monitoring_service._redis_queue_length",
            return_value=queue,
        ),
        patch(
            "chatbot_api.services.monitoring_service._celery_workers_alive",
            return_value=workers,
        ),
    ):
        resp = await client.get(
            "/api/v1/monitoring/health", headers=DEV_USER_HEADER
        )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_monitoring_health_aggregates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify counts/avgs change correctly when we add a known seed.

    The test DB may already contain committed rows from other modules
    (workers commit via their own engines). We assert *deltas* instead of
    absolute totals to stay robust across test ordering.
    """
    before = await _fetch_health(client, queue=3, workers=1)
    await _seed_messages(db_session)
    after = await _fetch_health(client, queue=3, workers=1)

    assert after["messages"]["last_hour"] - before["messages"]["last_hour"] == 5
    assert after["messages"]["last_24h"] - before["messages"]["last_24h"] == 5
    assert (
        after["tokens"]["input_today"] - before["tokens"]["input_today"]
        == 180
    )
    assert (
        after["tokens"]["output_today"] - before["tokens"]["output_today"]
        == 90
    )
    delta_classified = (
        after["intent_classifier"]["classified_last_24h"]
        - before["intent_classifier"]["classified_last_24h"]
    )
    assert delta_classified == 3
    assert after["queue"]["pending"] == 3
    assert after["queue"]["workers_alive"] == 1


@pytest.mark.asyncio
async def test_monitoring_health_responds_with_optional_metrics(
    client: AsyncClient,
) -> None:
    """Empty / sparse data: percentages may be None but the endpoint must not 500."""
    data = await _fetch_health(client, queue=0, workers=0)
    assert "messages" in data
    assert "intent_classifier" in data
    assert "tokens" in data
    assert data["queue"]["workers_alive"] == 0
    # p95 is None or a positive number; never crashes the response.
    assert (
        data["messages"]["p95_latency_ms"] is None
        or data["messages"]["p95_latency_ms"] >= 0
    )


@pytest.mark.asyncio
async def test_monitoring_counts_takeover_conversations(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_student(db_session, phone="+51900028050")
    conv = await make_conversation(
        db_session,
        student_phone="+51900028050",
        status=ConversationStatus.takeover,
    )
    assert conv.status == ConversationStatus.takeover

    with (
        patch(
            "chatbot_api.services.monitoring_service._redis_queue_length",
            return_value=0,
        ),
        patch(
            "chatbot_api.services.monitoring_service._celery_workers_alive",
            return_value=1,
        ),
    ):
        resp = await client.get(
            "/api/v1/monitoring/health", headers=DEV_USER_HEADER
        )
    assert resp.status_code == 200
    assert resp.json()["conversations"]["takeover"] >= 1
