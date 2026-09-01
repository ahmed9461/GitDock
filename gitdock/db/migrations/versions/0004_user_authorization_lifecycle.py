"""Add durable user-authorization lifecycle state.

Revision ID: 0004_user_authorization_lifecycle
Revises: 0003_repository_cache
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_user_authorization_lifecycle"
down_revision = "0003_repository_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "github_accounts",
        sa.Column("credential_generation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "pending_confirmations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("target_fingerprint", sa.String(length=160), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("risk_tier", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("token_digest", name="uq_pending_confirmations_token_digest"),
    )
    op.create_index("ix_pending_confirmations_user_id", "pending_confirmations", ["user_id"])
    op.create_index(
        "ix_pending_confirmations_token_digest", "pending_confirmations", ["token_digest"]
    )
    op.create_index(
        "ix_pending_confirmations_operation_type", "pending_confirmations", ["operation_type"]
    )
    op.create_index("ix_pending_confirmations_expires_at", "pending_confirmations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_confirmations_expires_at", table_name="pending_confirmations")
    op.drop_index("ix_pending_confirmations_operation_type", table_name="pending_confirmations")
    op.drop_index("ix_pending_confirmations_token_digest", table_name="pending_confirmations")
    op.drop_index("ix_pending_confirmations_user_id", table_name="pending_confirmations")
    op.drop_table("pending_confirmations")
    op.drop_column("github_accounts", "credential_generation")
