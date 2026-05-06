from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MetricsDaily(Base):
    __tablename__ = "metrics_daily"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    conversations_total: Mapped[int] = mapped_column(default=0, nullable=False)
    conversations_takeover: Mapped[int] = mapped_column(default=0, nullable=False)
    messages_total: Mapped[int] = mapped_column(default=0, nullable=False)
    avg_response_ms: Mapped[int | None] = mapped_column(nullable=True)
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    intent_distribution: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, nullable=False)
