"""Add filter_names to users for user-created filters (collections) before any recipe has them.

Revision ID: 0018_user_filter_names
Revises: 0017_trial_device_id
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0018_user_filter_names"
down_revision = "0017_trial_device_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("filter_names", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("users", "filter_names")
