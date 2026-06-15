"""Helpers de zona horaria del negocio (America/Lima).

Los timestamps se guardan en UTC (naive). Para filtrar/agrupar por "día" según
lo que ve el usuario hay que convertirlos a hora de pared de Lima; si no, los
límites de día quedan corridos 5 horas. Lima es UTC-5 todo el año (sin DST).
"""

from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func

LOCAL_TZ = "America/Lima"
LOCAL_UTC_OFFSET = timedelta(hours=-5)


def to_local(col: Any) -> Any:
    """Expresión SQL: timestamp UTC (naive) → hora de pared de Lima."""
    return func.timezone(LOCAL_TZ, func.timezone("UTC", col))


def today_local_start() -> datetime:
    """Medianoche de hoy en Lima (naive), para comparar contra `to_local(col)`."""
    today_local = (datetime.now(UTC) + LOCAL_UTC_OFFSET).date()
    return datetime.combine(today_local, time.min)
