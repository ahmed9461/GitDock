"""Add restart-safe staged single-file writes.

Revision ID: 0006_file_write
Revises: 0005_audit_log
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_file_write"
down_revision = "0005_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "file_write_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("github_repository_id", sa.BigInteger(), nullable=False),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("repository_full_name", sa.String(length=511), nullable=False),
        sa.Column("repository_default_branch", sa.String(length=255), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("branch_head_sha", sa.String(length=128), nullable=False),
        sa.Column("expected_file_sha", sa.String(length=128), nullable=True),
        sa.Column("desired_blob_sha", sa.String(length=128), nullable=True),
        sa.Column("content_digest", sa.String(length=64), nullable=True),
        sa.Column("content_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("commit_message", sa.String(length=500), nullable=False),
        sa.Column("risk_tier", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_file_write_sessions_user_id", "file_write_sessions", ["user_id"])
    op.create_index(
        "ix_file_write_sessions_user_created_at",
        "file_write_sessions",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_file_write_sessions_target",
        "file_write_sessions",
        ["user_id", "github_repository_id", "branch", "path"],
    )


def downgrade() -> None:
    op.drop_index("ix_file_write_sessions_target", table_name="file_write_sessions")
    op.drop_index("ix_file_write_sessions_user_created_at", table_name="file_write_sessions")
    op.drop_index("ix_file_write_sessions_user_id", table_name="file_write_sessions")
    op.drop_table("file_write_sessions")
