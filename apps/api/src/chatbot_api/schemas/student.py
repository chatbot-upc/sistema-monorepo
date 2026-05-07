from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone_e164: str
    display_name: str | None
    first_seen_at: datetime
    last_seen_at: datetime
