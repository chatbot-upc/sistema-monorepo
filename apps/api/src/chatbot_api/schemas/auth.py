from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    id_token: str
    refresh_token: str
    token_type: str = "Bearer"  # noqa: S105
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    id_token: str
    token_type: str = "Bearer"  # noqa: S105
    expires_in: int
