from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Paleta de colores válidos para etiquetas (la UI mapea cada clave a un estilo).
TagColor = Literal["blue", "violet", "amber", "mint", "coral", "slate"]


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: TagColor = "blue"


class TagAssign(BaseModel):
    tag_id: int
