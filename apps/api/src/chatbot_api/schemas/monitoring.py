"""Schemas for the internal monitoring endpoint (SW-28)."""

from pydantic import BaseModel


class MessagesMetrics(BaseModel):
    last_hour: int
    last_24h: int
    avg_latency_ms: float | None
    p95_latency_ms: float | None


class IntentClassifierMetrics(BaseModel):
    classified_last_24h: int
    sbert_only_pct: float | None
    fallback_to_llm_pct: float | None


class TokensMetrics(BaseModel):
    input_today: int
    output_today: int


class ConversationsMetrics(BaseModel):
    open: int
    takeover: int
    closed_today: int


class QueueMetrics(BaseModel):
    pending: int
    workers_alive: int


class MonitoringHealth(BaseModel):
    messages: MessagesMetrics
    intent_classifier: IntentClassifierMetrics
    tokens: TokensMetrics
    conversations: ConversationsMetrics
    queue: QueueMetrics
