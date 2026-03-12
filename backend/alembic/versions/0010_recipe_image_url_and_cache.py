"""add recipe image_url and recipe_image_cache table

Revision ID: 0010_recipe_image
Revises: 0009_diet_tags
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa


revision = "0010_recipe_image"
down_revision = "0009_diet_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("image_url", sa.String(500), nullable=True),
    )
    op.create_table(
        "recipe_image_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cache_key", sa.String(255), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_recipe_image_cache_cache_key"),
        "recipe_image_cache",
        ["cache_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_recipe_image_cache_cache_key"), table_name="recipe_image_cache")
    op.drop_table("recipe_image_cache")
    op.drop_column("recipes", "image_url")
