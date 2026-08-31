"""Create initial identity/account tables.

Revision ID: 0001_identity_baseline
Revises: None
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_identity_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "telegram_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("telegram_user_id", name="uq_telegram_accounts_telegram_user_id"),
    )
    op.create_index(
        "ix_telegram_accounts_telegram_user_id", "telegram_accounts", ["telegram_user_id"]
    )
    op.create_table(
        "github_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("github_user_id", sa.BigInteger(), nullable=False),
        sa.Column("login", sa.String(length=255), nullable=False),
        sa.Column("encrypted_access_token", sa.LargeBinary(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.LargeBinary(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_key_version", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("github_user_id", name="uq_github_accounts_github_user_id"),
    )
    op.create_index("ix_github_accounts_github_user_id", "github_accounts", ["github_user_id"])
    op.create_table(
        "github_installations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("account_login", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("suspended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("permissions_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("installation_id", name="uq_github_installations_installation_id"),
    )
    op.create_index(
        "ix_github_installations_installation_id", "github_installations", ["installation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_github_installations_installation_id", table_name="github_installations")
    op.drop_table("github_installations")
    op.drop_index("ix_github_accounts_github_user_id", table_name="github_accounts")
    op.drop_table("github_accounts")
    op.drop_index("ix_telegram_accounts_telegram_user_id", table_name="telegram_accounts")
    op.drop_table("telegram_accounts")
    op.drop_table("users")
