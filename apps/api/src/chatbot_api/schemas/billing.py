from decimal import Decimal

from pydantic import BaseModel


class BillingImportResult(BaseModel):
    """Resultado de una carga de facturación desde archivo (SW-52)."""

    students: int
    inserted: int
    updated: int
    skipped: int
    errors: list[str]


class BillingOverview(BaseModel):
    """Estado actual de la facturación cargada, para el panel admin."""

    students: int
    installments: int
    pending_installments: int
    total_pending: Decimal
    currency: str = "PEN"
