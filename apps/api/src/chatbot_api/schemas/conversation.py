from datetime import datetime

from pydantic import BaseModel, ConfigDict

from chatbot_api.models.enums import ConversationStatus

from .message import MessageRead


class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_phone: str
    student_display_name: str | None
    status: ConversationStatus
    opened_at: datetime
    closed_at: datetime | None
    message_count: int
    last_message_preview: str | None


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_phone: str
    status: ConversationStatus
    opened_at: datetime
    closed_at: datetime | None
    closed_by: int | None
    takeover_admin: int | None
    messages: list[MessageRead]
