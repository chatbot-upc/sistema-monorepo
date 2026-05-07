from fastapi import APIRouter, Depends

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.models import Admin
from chatbot_api.schemas.admin import AdminRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=AdminRead)
async def me(admin: Admin = Depends(get_current_admin)) -> AdminRead:
    return AdminRead.model_validate(admin)
