"""Append-oriented audit records for user-triggered GitHub writes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from gitdock.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_user_created_at", "user_id", "created_at"),
        Index("ix_audit_log_operation_created_at", "operation", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    github_login: Mapped[str | None] = mapped_column(String(255))
    installation_id: Mapped[int | None] = mapped_column(BigInteger)
    github_repository_id: Mapped[int | None] = mapped_column(BigInteger)
    repository_full_name: Mapped[str | None] = mapped_column(String(511))
    github_request_id: Mapped[str | None] = mapped_column(String(255))
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
