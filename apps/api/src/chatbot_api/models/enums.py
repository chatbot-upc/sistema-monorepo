import enum


class AdminRole(enum.StrEnum):
    admin = "admin"
    supervisor = "supervisor"
    viewer = "viewer"


class ConversationStatus(enum.StrEnum):
    abierta = "abierta"
    cerrada = "cerrada"
    takeover = "takeover"


class MessageRole(enum.StrEnum):
    bot = "bot"
    student = "student"
    admin = "admin"


class DocumentSourceType(enum.StrEnum):
    upload = "upload"
    scraped = "scraped"
    link = "link"


class DocumentStatus(enum.StrEnum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    error = "error"


class NotificationStatus(enum.StrEnum):
    draft = "draft"
    scheduled = "scheduled"
    sending = "sending"
    sent = "sent"
    failed = "failed"
