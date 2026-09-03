"""Add append-oriented GitHub write audit log.

Revision ID: 0005_audit_log
Revises: 0004_user_auth_lifecycle
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_audit_log"
down_revision = "0004_user_auth_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("github_login", sa.String(length=255), nullable=True),
        sa.Column("installation_id", sa.BigInteger(), nullable=True),
        sa.Column("github_repository_id", sa.BigInteger(), nullable=True),
        sa.Column("repository_full_name", sa.String(length=511), nullable=True),
        sa.Column("github_request_id", sa.String(length=255), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_user_created_at", "audit_log", ["user_id", "created_at"])
    op.create_index("ix_audit_log_operation_created_at", "audit_log", ["operation", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_operation_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_user_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_table("audit_log")
