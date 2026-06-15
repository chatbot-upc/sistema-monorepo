from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from chatbot_api.models.enums import ConversationStatus

from .message import MessageRead
from .student_profile import StudentProfileRead
from .tag import TagRead


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4096)
    in_reply_to_id: int | None = None


class SendMessageResponse(BaseModel):
    message_id: int
    meta_message_id: str | None
    conversation_status: ConversationStatus


class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_phone: str
    display_name: str | None
    status: ConversationStatus
    opened_at: datetime
    closed_at: datetime | None
    message_count: int
    last_message_preview: str | None
    starred: bool = False


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_phone: str
    display_name: str | None = None
    email: str | None = None
    status: ConversationStatus
    opened_at: datetime
    closed_at: datetime | None
    closed_by: int | None
    takeover_admin: int | None
    starred: bool = False
    student_profile: StudentProfileRead | None = None
    tags: list[TagRead] = []
    messages: list[MessageRead]


class ContactUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=255)


class StarUpdate(BaseModel):
    starred: bool


class ConversationHistory(BaseModel):
    total_conversations: int
    total_messages: int
    first_contact: datetime | None = None
