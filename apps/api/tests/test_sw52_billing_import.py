"""SW-52 (EP08) — carga de facturación simulada desde archivo (Excel/CSV)."""

from __future__ import annotations

import io

import pytest
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import StudentBillingInstallment
from chatbot_api.models.enums import BillingStatus
from chatbot_api.services import billing_import

_HEADER = "telefono,ciclo,numero,concepto,monto,vencimiento,estado,fecha_pago"


def _csv(rows: list[str]) -> bytes:
    return ("\n".join([_HEADER, *rows])).encode("utf-8")


def test_parse_csv_valid() -> None:
    content = _csv(
        [
            "+51999000001,2026-1,1,Matrícula,850.00,2026-03-15,pagado,2026-03-10",
            "+51999000001,2026-1,2,Cuota 1,1850.00,2026-04-15,pendiente,",
        ]
    )
    rows, errors = billing_import.parse("f.csv", content)
    assert errors == []
    assert len(rows) == 2
    assert rows[0].phone_e164 == "+51999000001"
    assert rows[0].status == BillingStatus.pagado
    assert str(rows[1].amount) == "1850.00"
    assert rows[1].status == BillingStatus.pendiente


def test_parse_normalizes_phone_and_thousands_separator() -> None:
    rows, errors = billing_import.parse(
        "f.csv", _csv(["51999000002,2026-1,1,Pensión,\"1,850.00\",2026-04-15,,"])
    )
    assert errors == []
    assert rows[0].phone_e164 == "+51999000002"  # prepende '+'
    assert str(rows[0].amount) == "1850.00"  # quita separador de miles
    assert rows[0].status == BillingStatus.pendiente  # estado vacío → pendiente


def test_parse_missing_required_columns() -> None:
    bad = "telefono,ciclo,concepto\n+51999000003,2026-1,Pensión".encode()
    rows, errors = billing_import.parse("f.csv", bad)
    assert rows == []
    assert any("columnas obligatorias" in e for e in errors)


def test_parse_invalid_row_is_skipped_with_error() -> None:
    content = _csv(
        [
            "+51999000004,2026-1,1,OK,100.00,2026-04-15,pendiente,",
            ",2026-1,2,SinTelefono,100.00,2026-04-15,pendiente,",  # phone vacío
            "+51999000004,2026-1,X,NumMalo,100.00,2026-04-15,pendiente,",  # número inválido
        ]
    )
    rows, errors = billing_import.parse("f.csv", content)
    assert len(rows) == 1
    assert len(errors) == 2
    assert errors[0].startswith("Fila 3")
    assert errors[1].startswith("Fila 4")


def test_parse_unsupported_format() -> None:
    # parse propaga ValueError; import_billing_file lo captura y lo vuelve error.
    with pytest.raises(ValueError, match="Formato no soportado"):
        billing_import.parse("f.txt", b"cualquier cosa")


def test_parse_xlsx() -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(_HEADER.split(","))
    ws.append(
        ["+51999000005", "2026-1", 1, "Matrícula", 850.0, "2026-03-15", "pagado", ""]
    )
    buf = io.BytesIO()
    wb.save(buf)
    rows, errors = billing_import.parse("f.xlsx", buf.getvalue())
    assert errors == []
    assert len(rows) == 1
    assert rows[0].phone_e164 == "+51999000005"
    assert rows[0].status == BillingStatus.pagado


@pytest.mark.asyncio
async def test_import_is_idempotent(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51999050001"
    content = _csv(
        [
            f"{phone},2026-1,1,Matrícula,850.00,2026-03-15,pagado,2026-03-10",
            f"{phone},2026-1,2,Cuota 1,1850.00,2026-04-15,pendiente,",
        ]
    )

    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        first = await billing_import.import_billing_file(
            db, filename="f.csv", content=content
        )
    assert first.inserted == 2
    assert first.updated == 0
    assert first.skipped == 0
    assert first.students == 1

    # Reimportar el mismo archivo → actualiza, no duplica.
    async with factory() as db:
        second = await billing_import.import_billing_file(
            db, filename="f.csv", content=content
        )
    assert second.inserted == 0
    assert second.updated == 2

    async with factory() as db:
        rows = (
            await db.execute(
                select(StudentBillingInstallment).where(
                    StudentBillingInstallment.phone_e164 == phone
                )
            )
        ).scalars().all()
    assert len(rows) == 2  # sin duplicados
    await engine.dispose()
