from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    author_admin_id: int | None
    author_name: str | None = None
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class NoteUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
