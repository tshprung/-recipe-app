"""Add device_id to trial_sessions for resuming trial after sign-out.

Revision ID: 0017_trial_device_id
Revises: 0016_starter_no_images
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0017_trial_device_id"
down_revision = "0016_starter_no_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trial_sessions",
        sa.Column("device_id", sa.String(64), nullable=True),
    )
    op.create_index(
        op.f("ix_trial_sessions_device_id"),
        "trial_sessions",
        ["device_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_trial_sessions_device_id"), table_name="trial_sessions")
    op.drop_column("trial_sessions", "device_id")
