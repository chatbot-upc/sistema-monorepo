from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.schemas.billing import BillingImportResult, BillingOverview
from chatbot_api.services import billing_import

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/overview", response_model=BillingOverview)
async def overview(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> BillingOverview:
    return await billing_import.get_overview(db)


@router.post("/import", response_model=BillingImportResult)
async def import_billing(
    file: UploadFile = File(...),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> BillingImportResult:
    """Carga simulada de facturación desde Excel/CSV (SW-52). Upsert idempotente
    por (phone_e164, cycle, number)."""
    content = await file.read()
    return await billing_import.import_billing_file(
        db, filename=file.filename, content=content
    )
