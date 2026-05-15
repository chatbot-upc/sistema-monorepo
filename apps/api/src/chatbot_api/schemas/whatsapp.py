"""Pydantic models for Meta WhatsApp Cloud API webhook payload.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
We model only the fields we consume; unknown fields are ignored.
"""

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    from_phone: str = Field(alias="from")
    timestamp: str
    type: str
    text: WhatsAppTextBody | None = None


class WhatsAppContactProfile(BaseModel):
    name: str | None = None


class WhatsAppContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wa_id: str
    profile: WhatsAppContactProfile | None = None


class WhatsAppChangeValue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messaging_product: str | None = None
    contacts: list[WhatsAppContact] = Field(default_factory=list)
    messages: list[WhatsAppMessage] = Field(default_factory=list)


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
    from_phone: str
    display_name: str | None
    text: str
    timestamp: str
