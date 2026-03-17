"""Add google_oauth_tokens table for Google Calendar integration

Revision ID: 0021_google_oauth_tokens
Revises: 0020_meal_plans
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0021_google_oauth_tokens"
down_revision: Union[str, None] = "0020_meal_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "google_oauth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="google"),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_google_oauth_tokens_id"), "google_oauth_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_google_oauth_tokens_user_id"), "google_oauth_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_google_oauth_tokens_user_id"), table_name="google_oauth_tokens")
    op.drop_index(op.f("ix_google_oauth_tokens_id"), table_name="google_oauth_tokens")
    op.drop_table("google_oauth_tokens")

