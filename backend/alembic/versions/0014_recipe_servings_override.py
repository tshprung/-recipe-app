"""add servings_override to recipes

Revision ID: 0014_servings_override
Revises: 0013_trial_ip_whitelist
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


revision = "0014_servings_override"
down_revision = "0013_trial_ip_whitelist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("servings_override", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recipes", "servings_override")
