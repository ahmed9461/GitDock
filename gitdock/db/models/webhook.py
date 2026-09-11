"""Durable inbox state for authenticated GitHub webhook deliveries."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from gitdock.db.base import Base


class GitHubWebhookDelivery(Base):
    __tablename__ = "github_webhook_deliveries"
    __table_args__ = (
        Index(
            "ix_github_webhook_deliveries_work",
            "status",
            "next_attempt_at",
            "created_at",
        ),
        Index("ix_github_webhook_deliveries_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_size: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
