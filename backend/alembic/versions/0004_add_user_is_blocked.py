"""add is_blocked to users

Revision ID: 0004_add_user_is_blocked
Revises: 0003_shopping_list_cache
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_user_is_blocked"
down_revision = "0003_shopping_list_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "is_blocked")
