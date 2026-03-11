"""add shopping_list_cache table

Revision ID: 0003_shopping_list_cache
Revises: 0002_add_target_zip
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa

revision = "0003_shopping_list_cache"
down_revision = "0002_add_target_zip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_list_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_ids_snapshot", sa.JSON(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopping_list_cache_id", "shopping_list_cache", ["id"])
    op.create_index("ix_shopping_list_cache_user_id", "shopping_list_cache", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_shopping_list_cache_user_id", table_name="shopping_list_cache")
    op.drop_index("ix_shopping_list_cache_id", table_name="shopping_list_cache")
    op.drop_table("shopping_list_cache")
