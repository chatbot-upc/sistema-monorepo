"""Pydantic models for Meta WhatsApp Cloud API webhook payload.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
We model only the fields we consume; unknown fields are ignored.
"""

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppContext(BaseModel):
    """Cita nativa entrante: el `id` es el wamid del mensaje original (nuestro)."""

    model_config = ConfigDict(extra="ignore")

    id: str


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    from_phone: str = Field(alias="from")
    timestamp: str
    type: str
    text: WhatsAppTextBody | None = None
    context: WhatsAppContext | None = None


class WhatsAppContactProfile(BaseModel):
    name: str | None = None


class WhatsAppContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wa_id: str
    profile: WhatsAppContactProfile | None = None


class WhatsAppStatus(BaseModel):
    """Acuse de un saliente nuestro: id = wamid, status = sent/delivered/read/failed."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: str
    timestamp: str | None = None
    recipient_id: str | None = None


class WhatsAppChangeValue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messaging_product: str | None = None
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
    from_phone: str
    display_name: str | None
    text: str
    timestamp: str
    context_wamid: str | None = None


class ParsedStatus(BaseModel):
    """Acuse plano de un mensaje saliente, listo para actualizar delivery_status."""

    meta_message_id: str
    status: str
