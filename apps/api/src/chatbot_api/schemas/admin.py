from datetime import datetime

from pydantic import BaseModel, ConfigDict

from chatbot_api.models.enums import AdminRole


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: AdminRole
    active: bool
    created_at: datetime
