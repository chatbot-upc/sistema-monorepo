"""Siembra perfiles académicos (simulados) desde data-alumnos.xlsx.

One-shot de dev/demo (como bulk_ingest). El xlsx vive en la raíz del repo y NO
forma parte del runtime; en prod la data vendría de otra fuente. Idempotente:
upsert por phone_e164.

Requiere openpyxl (no es dep del proyecto):
    uv run --with openpyxl python scripts/seed_student_profiles.py
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from chatbot_api.core.db import get_session_factory
from chatbot_api.models import StudentProfile

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
XLSX_PATH = REPO_ROOT / "data-alumnos.xlsx"


def _normalize_phone(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(" ", "")
    if not s:
        return None
    if s.startswith("+"):
        return s
    return f"+{s}"


def _to_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return None


def _to_str(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _to_dt(raw: Any) -> datetime | None:
    return raw if isinstance(raw, datetime) else None


def _parse_rows() -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb["Final"]
    rows = list(ws.iter_rows(values_only=True))[1:]  # skip header
    parsed: list[dict[str, Any]] = []
    for r in rows:
        phone = _normalize_phone(r[1])
        name = _to_str(r[0])
        if not phone or not name:
            continue
        parsed.append(
            {
                "phone_e164": phone,
                "full_name": name,
                "career": _to_str(r[2]),
                "cycle": _to_int(r[3]),
                "campus": _to_str(r[4]),
                "modality": _to_str(r[5]),
                "academic_status": _to_str(r[6]),
                "failed_courses": _to_str(r[7]),
                "enrollment_turn": _to_dt(r[8]),
                "english_level": _to_int(r[9]),
                "elective_credits": _to_int(r[10]),
                "internship_credits": _to_int(r[11]),
            }
        )
    return parsed


async def _seed() -> None:
    records = _parse_rows()
    factory = get_session_factory()
    inserted = 0
    updated = 0
    async with factory() as db:
        for rec in records:
            existing = await db.get(StudentProfile, rec["phone_e164"])
            if existing is None:
                db.add(StudentProfile(**rec))
                inserted += 1
            else:
                for key, value in rec.items():
                    setattr(existing, key, value)
                updated += 1
        await db.commit()
    print(
        f"Seed completo: {inserted} insertados, {updated} actualizados, "
        f"{len(records)} total desde {XLSX_PATH.name}"
    )


if __name__ == "__main__":
    asyncio.run(_seed())
