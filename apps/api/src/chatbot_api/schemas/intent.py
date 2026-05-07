from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class IntentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    examples: list[Any]
    active: bool
    created_at: datetime
