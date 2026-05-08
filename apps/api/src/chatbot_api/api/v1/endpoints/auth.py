from fastapi import APIRouter, Depends, status

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.models import Admin
from chatbot_api.schemas.admin import AdminRead
from chatbot_api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
)
from chatbot_api.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login", response_model=TokenResponse, status_code=status.HTTP_200_OK
)
async def login(req: LoginRequest) -> TokenResponse:
    tokens = await auth_service.login(email=req.email, password=req.password)
    return TokenResponse(
        access_token=tokens["access_token"],
        id_token=tokens["id_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(req: RefreshRequest) -> TokenRefreshResponse:
    tokens = await auth_service.refresh(refresh_token=req.refresh_token)
    return TokenRefreshResponse(
        access_token=tokens["access_token"],
        id_token=tokens["id_token"],
        expires_in=tokens["expires_in"],
    )


@router.get("/me", response_model=AdminRead)
async def me(admin: Admin = Depends(get_current_admin)) -> AdminRead:
    return AdminRead.model_validate(admin)
