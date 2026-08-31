"""Durable GitHub authorization state for restart-safe OAuth/install flows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from gitdock.db.base import Base


class GitHubAuthorizationState(Base):
    __tablename__ = "github_authorization_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    state_digest: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    flow: Mapped[str] = mapped_column(String(32), nullable=False)
    encrypted_code_verifier: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    code_verifier_key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
