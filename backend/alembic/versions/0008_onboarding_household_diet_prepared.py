"""onboarding: household_adults, household_kids, diet_filters, prepared_starter_recipes

Revision ID: 0008_onboarding
Revises: 0007_dish_preferences
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa


revision = "0008_onboarding"
down_revision = "0007_dish_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("household_adults", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("household_kids", sa.Integer(), nullable=True),
    )
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    default_json = sa.text("'[]'::json") if dialect == "postgresql" else sa.text("'[]'")
    op.add_column(
        "users",
        sa.Column("diet_filters", sa.JSON(), nullable=False, server_default=default_json),
    )
    op.create_table(
        "prepared_starter_recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_token", sa.String(64), nullable=False),
        sa.Column("recipes_data", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prepared_starter_recipes_claim_token"),
        "prepared_starter_recipes",
        ["claim_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_prepared_starter_recipes_claim_token"),
        table_name="prepared_starter_recipes",
    )
    op.drop_table("prepared_starter_recipes")
    op.drop_column("users", "diet_filters")
    op.drop_column("users", "household_kids")
    op.drop_column("users", "household_adults")
