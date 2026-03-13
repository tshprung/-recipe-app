"""add recipe collections (user-defined tags)

Revision ID: 0015_recipe_collections
Revises: 0014_servings_override
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


revision = "0015_recipe_collections"
down_revision = "0014_servings_override"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("collections", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("recipes", "collections")
