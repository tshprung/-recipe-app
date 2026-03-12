"""add trial_sessions table for anonymous trial quota

Revision ID: 0011_trial_sessions
Revises: 0010_recipe_image
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa


revision = "0011_trial_sessions"
down_revision = "0010_recipe_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trial_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_id", sa.String(32), unique=True, nullable=False, index=True),
        sa.Column("country", sa.String(10), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("used_actions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ip_address", sa.String(45), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("trial_sessions")
