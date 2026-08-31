"""Create durable GitHub authorization state table.

Revision ID: 0002_github_auth_state
Revises: 0001_identity_baseline
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_github_auth_state"
down_revision = "0001_identity_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_authorization_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("state_digest", sa.String(length=64), nullable=False),
        sa.Column("flow", sa.String(length=32), nullable=False),
        sa.Column("candidate_installation_id", sa.BigInteger(), nullable=True),
        sa.Column("encrypted_code_verifier", sa.LargeBinary(), nullable=False),
        sa.Column("code_verifier_key_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("state_digest", name="uq_github_authorization_states_state_digest"),
    )
    op.create_index(
        "ix_github_authorization_states_state_digest",
        "github_authorization_states",
        ["state_digest"],
    )
    op.create_index(
        "ix_github_authorization_states_expires_at",
        "github_authorization_states",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_github_authorization_states_expires_at",
        table_name="github_authorization_states",
    )
    op.drop_index(
        "ix_github_authorization_states_state_digest",
        table_name="github_authorization_states",
    )
    op.drop_table("github_authorization_states")
