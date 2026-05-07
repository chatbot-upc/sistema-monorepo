from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from chatbot_api.models.enums import NotificationStatus


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_name: str
    audience_filter: dict[str, Any]
    scheduled_at: datetime | None
    sent_at: datetime | None
    status: NotificationStatus
    sent_count: int
    failed_count: int
    created_at: datetime
