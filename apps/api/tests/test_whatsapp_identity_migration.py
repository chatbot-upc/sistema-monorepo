"""Exercise the real Alembic upgrade/downgrade with preexisting synthetic data."""

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

API_DIR = Path(__file__).parent.parent


async def sql(url, statements):
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            results = []
            for statement in statements:
                result = await conn.execute(text(statement))
                results.append(result.fetchall() if result.returns_rows else None)
            return results
    finally:
        await engine.dispose()


def test_upgrade_backfill_phone_roundtrip_and_lossless_guard():
    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as container:
        url = container.get_connection_url()
        cfg = Config(str(API_DIR / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", url)
        cfg.set_main_option("script_location", str(API_DIR / "alembic"))
        old = "0023_seed_intent_consulta_pagos"
        command.upgrade(cfg, old)
        asyncio.run(
            sql(
                url,
                [
                    "INSERT INTO students(phone_e164, display_name, email) VALUES "
                    "('+51900008901','Synthetic Student','synthetic@example.test')",
                    "INSERT INTO conversations(id, student_phone, status, meta) VALUES "
                    "(8101,'+51900008901','abierta','{}'), (8102,'+51900008901','cerrada','{}')",
                    "INSERT INTO messages(id,conversation_id,role,content,retrieved_chunks) "
                    "VALUES (8201,8101,'student','Synthetic history','[]')",
                    "INSERT INTO tags(id,name,color) VALUES (8301,'Synthetic tag','blue')",
                    "INSERT INTO conversation_tags(conversation_id,tag_id) VALUES (8101,8301)",
                    "INSERT INTO student_profiles(phone_e164,full_name,career) VALUES "
                    "('+51900008901','Synthetic Academic','Synthetic Career')",
                    "INSERT INTO "
                    "student_billing_installments(id,phone_e164,cycle,number,concept,amount,due_"
                    "date) VALUES (8401,'+51900008901','2026-1',1,'Synthetic "
                    "Tuition',123.45,'2026-11-01')",
                ],
            )
        )
        snapshots = [
            "SELECT phone_e164,display_name,email,first_seen_at,last_seen_at FROM students "
            "ORDER BY phone_e164",
            "SELECT id,name,color FROM tags ORDER BY id",
            "SELECT id,student_phone,status,meta FROM conversations ORDER BY id",
            "SELECT id,conversation_id,content FROM messages ORDER BY id",
            "SELECT conversation_id,tag_id FROM conversation_tags",
            "SELECT phone_e164,full_name,career FROM student_profiles",
            "SELECT id,phone_e164,amount FROM student_billing_installments",
        ]
        before = asyncio.run(sql(url, snapshots))
        command.upgrade(cfg, "head")
        assert asyncio.run(sql(url, snapshots)) == before
        result = asyncio.run(
            sql(
                url,
                [
                    "SELECT c.id,c.student_id,s.id,s.phone_e164 FROM conversations c JOIN "
                    "students s ON s.id=c.student_id ORDER BY c.id",
                    "INSERT INTO students(display_name) VALUES ('BSUID placeholder') RETURNING id",
                ],
            )
        )
        assert [row[0] for row in result[0]] == [8101, 8102]
        assert all(row[1] == row[2] and row[3] == "+51900008901" for row in result[0])
        assert result[1][0][0] > result[0][0][1]  # BIGSERIAL continues after backfill.
        with pytest.raises(RuntimeError, match="losslessly"):
            command.downgrade(cfg, old)
        asyncio.run(sql(url, ["DELETE FROM students WHERE phone_e164 IS NULL"]))
        command.downgrade(cfg, old)
        assert asyncio.run(sql(url, snapshots)) == before
        command.upgrade(cfg, "head")
        # Even a phone-bearing alias must not silently disappear on downgrade.
        asyncio.run(
            sql(
                url,
                [
                    "INSERT INTO whatsapp_identities(scope,user_id,student_id) SELECT "
                    "'portfolio:test','opaque-user',id FROM students"
                ],
            )
        )
        with pytest.raises(RuntimeError, match="losslessly"):
            command.downgrade(cfg, old)
        assert asyncio.run(sql(url, snapshots)) == before
