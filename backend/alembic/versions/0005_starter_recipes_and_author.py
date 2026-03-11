"""add starter_recipes_added to users, author fields to recipes

Revision ID: 0005_starter_recipes_author
Revises: 0004_add_user_is_blocked
Create Date: 2026-03-11

"""

from alembic import op
import sqlalchemy as sa


revision = "0005_starter_recipes_author"
down_revision = "0004_add_user_is_blocked"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("starter_recipes_added", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("recipes", sa.Column("author_name", sa.String(255), nullable=True))
    op.add_column("recipes", sa.Column("author_bio", sa.Text(), nullable=True))
    op.add_column("recipes", sa.Column("author_image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "author_image_url")
    op.drop_column("recipes", "author_bio")
    op.drop_column("recipes", "author_name")
    op.drop_column("users", "starter_recipes_added")
