from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    version: int
    content: str
    active: bool
    created_at: datetime


class PromptVersionCreate(BaseModel):
    content: str = Field(min_length=20)


class PromptVersionUpdate(BaseModel):
    content: str = Field(min_length=20)
