from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_e164: str | None
    whatsapp_user_id: str | None = None
    whatsapp_username: str | None = None
    display_name: str | None
    first_seen_at: datetime
    last_seen_at: datetime
