from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IntentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    examples: list[Any]
    active: bool
    created_at: datetime


class IntentCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
        description="Clave técnica en snake_case (inmutable tras crear).",
    )
    description: str | None = None
    examples: list[str] = Field(min_length=1)


class IntentUpdate(BaseModel):
    description: str | None = None
    examples: list[str] | None = Field(default=None, min_length=1)
    active: bool | None = None
