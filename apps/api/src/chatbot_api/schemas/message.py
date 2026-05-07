from datetime import datetime

from pydantic import BaseModel, ConfigDict

from chatbot_api.models.enums import MessageRole


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: MessageRole
    content: str
    intent_id: int | None
    input_tokens: int | None
    output_tokens: int | None
    model_used: str | None
    latency_ms: int | None
    created_at: datetime
