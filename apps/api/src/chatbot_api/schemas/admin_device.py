from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, max_length=2048)
    platform: str = Field(default="web", max_length=20)
    user_agent: str | None = Field(default=None, max_length=500)


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_id: int
    platform: str
    user_agent: str | None
    created_at: datetime
