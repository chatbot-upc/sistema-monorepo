"""Pydantic models for Meta WhatsApp Cloud API webhook payload.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
We model only the fields we consume; unknown fields are ignored.
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppContext(BaseModel):
    """Cita nativa entrante: el `id` es el wamid del mensaje original (nuestro)."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None


class WhatsAppSystem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    wa_id: str | None = None
    user_id: str | None = None
    parent_user_id: str | None = None
    previous_user_id: str | None = None
    previous_parent_user_id: str | None = None

    @field_validator(
        "wa_id", "user_id", "parent_user_id", "previous_user_id", "previous_parent_user_id"
    )
    @classmethod
    def empty_identity_is_absent(cls, value: str | None) -> str | None:
        return value if value and value.strip() else None


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    from_phone: str | None = Field(default=None, alias="from")
    from_user_id: str | None = None
    from_parent_user_id: str | None = None
    timestamp: str
    type: str
    text: WhatsAppTextBody | None = None
    context: WhatsAppContext | None = None
    system: WhatsAppSystem | None = None

    @field_validator("from_phone", "from_user_id", "from_parent_user_id")
    @classmethod
    def empty_identity_is_absent(cls, value: str | None) -> str | None:
        return value if value and value.strip() else None

    @model_validator(mode="after")
    def validate_event_identity(self) -> Self:
        if self.type == "text":
            if self.text is None:
                raise ValueError("text message requires text.body")
            if not any(value and value.strip() for value in (self.from_phone, self.from_user_id)):
                raise ValueError("text message requires from or from_user_id")
        elif self.type == "system":
            if self.system is None:
                raise ValueError("system message requires system")
            if self.system.type == "user_changed_user_id" and not (
                self.system.user_id and self.system.user_id.strip()
            ):
                raise ValueError("user_changed_user_id requires system.user_id")
            if self.system.type == "user_changed_number" and not (
                self.system.wa_id and self.system.wa_id.strip()
            ):
                raise ValueError("user_changed_number requires system.wa_id")
        return self


class WhatsAppContactProfile(BaseModel):
    name: str | None = None
    username: str | None = None


class WhatsAppContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wa_id: str | None = None
    user_id: str | None = None
    parent_user_id: str | None = None
    profile: WhatsAppContactProfile | None = None

    @field_validator("wa_id", "user_id", "parent_user_id")
    @classmethod
    def empty_identity_is_absent(cls, value: str | None) -> str | None:
        return value if value and value.strip() else None


class WhatsAppStatus(BaseModel):
    """Acuse de un saliente nuestro: id = wamid, status = sent/delivered/read/failed."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: str
    timestamp: str | None = None
    recipient_id: str | None = None
    recipient_user_id: str | None = None
    recipient_parent_user_id: str | None = None


class WhatsAppMetadata(BaseModel):
    phone_number_id: str | None = None


class WhatsAppChangeValue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messaging_product: str | None = None
    metadata: WhatsAppMetadata | None = None
    contacts: list[WhatsAppContact] = Field(default_factory=list)
    messages: list[WhatsAppMessage] = Field(default_factory=list)
    statuses: list[WhatsAppStatus] = Field(default_factory=list)


class WhatsAppChange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: WhatsAppChangeValue
    field: str | None = None


class WhatsAppEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    changes: list[WhatsAppChange] = Field(default_factory=list)


class WhatsAppWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    object: str | None = None
    entry: list[WhatsAppEntry] = Field(default_factory=list)


class ParsedInboundMessage(BaseModel):
    """Flat shape consumed by the Celery worker — JSON-serializable."""

    meta_message_id: str
    from_phone: str | None = None
    from_user_id: str | None = None
    from_parent_user_id: str | None = None
    username: str | None = None
    identity_scope: str | None = None
    business_phone_number_id: str | None = None
    display_name: str | None = None
    text: str
    timestamp: str
    context_wamid: str | None = None


class ParsedIdentityChange(BaseModel):
    """Official identity rotation, kept separate from user text and shared vCards."""

    meta_message_id: str
    timestamp: str
    system_type: Literal["user_changed_number", "user_changed_user_id"]
    identity_scope: str | None = None
    business_phone_number_id: str | None = None
    user_id: str | None = None
    previous_user_id: str | None = None
    from_phone: str | None = None
    new_wa_id: str | None = None  # Routing metadata; never a confirmed actual phone.
    parent_user_id: str | None = None
    previous_parent_user_id: str | None = None


class ParsedStatus(BaseModel):
    """Acuse plano de un mensaje saliente, listo para actualizar delivery_status."""

    meta_message_id: str
    status: str
