"""Create minimal repository metadata cache.

Revision ID: 0003_repository_cache
Revises: 0002_github_auth_state
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_repository_cache"
down_revision = "0002_github_auth_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repositories_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "installation_db_id",
            sa.Integer(),
            sa.ForeignKey("github_installations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("github_repository_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_login", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=511), nullable=False),
        sa.Column("html_url", sa.String(length=1024), nullable=False),
        sa.Column("private", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("fork", sa.Boolean(), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("github_pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cached_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "user_id",
            "github_repository_id",
            name="uq_repositories_cache_user_repository",
        ),
    )
    op.create_index("ix_repositories_cache_user_id", "repositories_cache", ["user_id"])
    op.create_index(
        "ix_repositories_cache_installation_db_id", "repositories_cache", ["installation_db_id"]
    )
    op.create_index(
        "ix_repositories_cache_github_repository_id",
        "repositories_cache",
        ["github_repository_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_repositories_cache_github_repository_id", table_name="repositories_cache")
    op.drop_index("ix_repositories_cache_installation_db_id", table_name="repositories_cache")
    op.drop_index("ix_repositories_cache_user_id", table_name="repositories_cache")
    op.drop_table("repositories_cache")
