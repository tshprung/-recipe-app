"""add trial_ip_whitelist table for exempting IPs from trial limits

Revision ID: 0013_trial_ip_whitelist
Revises: 0012_trial_session
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa


revision = "0013_trial_ip_whitelist"
down_revision = "0012_trial_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trial_ip_whitelist",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ip_address", sa.String(45), nullable=False, unique=True),
        sa.Column("label", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_trial_ip_whitelist_ip_address",
        "trial_ip_whitelist",
        ["ip_address"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_trial_ip_whitelist_ip_address", table_name="trial_ip_whitelist")
    op.drop_table("trial_ip_whitelist")

