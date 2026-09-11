"""Restart-safe staging for one-file GitHub writes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from gitdock.db.base import Base


class FileWriteSession(Base):
    __tablename__ = "file_write_sessions"
    __table_args__ = (
        Index("ix_file_write_sessions_user_created_at", "user_id", "created_at"),
        Index(
            "ix_file_write_sessions_target",
            "user_id",
            "github_repository_id",
            "branch",
            "path",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    github_repository_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    installation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    repository_full_name: Mapped[str] = mapped_column(String(511), nullable=False)
    repository_default_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    branch_head_sha: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_file_sha: Mapped[str | None] = mapped_column(String(128))
    desired_blob_sha: Mapped[str | None] = mapped_column(String(128))
    content_digest: Mapped[str | None] = mapped_column(String(64))
    content_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)
    commit_message: Mapped[str] = mapped_column(String(500), nullable=False)
    risk_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
