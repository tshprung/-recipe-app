"""add dish_preferences to users

Revision ID: 0007_dish_preferences
Revises: 0006_allergens_time_rating
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa


revision = "0007_dish_preferences"
down_revision = "0006_allergens_time_rating"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    default_json = sa.text("'[]'::json") if dialect == "postgresql" else sa.text("'[]'")
    op.add_column(
        "users",
        sa.Column("dish_preferences", sa.JSON(), nullable=False, server_default=default_json),
    )


def downgrade() -> None:
    op.drop_column("users", "dish_preferences")
