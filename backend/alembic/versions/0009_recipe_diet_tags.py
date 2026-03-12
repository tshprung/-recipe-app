"""add diet_tags to recipes (e.g. kosher for starter recipes)

Revision ID: 0009_diet_tags
Revises: 0008_onboarding
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa


revision = "0009_diet_tags"
down_revision = "0008_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    default_json = sa.text("'[]'::json") if dialect == "postgresql" else sa.text("'[]'")
    op.add_column(
        "recipes",
        sa.Column("diet_tags", sa.JSON(), nullable=False, server_default=default_json),
    )


def downgrade() -> None:
    op.drop_column("recipes", "diet_tags")
