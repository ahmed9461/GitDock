"""Add durable GitHub webhook delivery inbox.

Revision ID: 0007_webhook_inbox
Revises: 0006_file_write
Create Date: 2026-09-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_webhook_inbox"
down_revision = "0006_file_write"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("delivery_id", sa.String(length=128), nullable=False),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_size", sa.Integer(), nullable=False),
        sa.Column("payload_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("delivery_id", name="uq_github_webhook_deliveries_delivery_id"),
    )
    op.create_index(
        "ix_github_webhook_deliveries_work",
        "github_webhook_deliveries",
        ["status", "next_attempt_at", "created_at"],
    )
    op.create_index(
        "ix_github_webhook_deliveries_expires_at",
        "github_webhook_deliveries",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_github_webhook_deliveries_expires_at", table_name="github_webhook_deliveries")
    op.drop_index("ix_github_webhook_deliveries_work", table_name="github_webhook_deliveries")
    op.drop_table("github_webhook_deliveries")
