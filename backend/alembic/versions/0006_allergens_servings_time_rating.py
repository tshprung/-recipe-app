"""add allergens, default servings, times, rating

Revision ID: 0006_allergens_time_rating
Revises: 0005_starter_recipes_author
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa


# NOTE: Alembic's default alembic_version.version_num is VARCHAR(32).
# Keep revision ids <= 32 chars to avoid Postgres StringDataRightTruncation.
revision = "0006_allergens_time_rating"
down_revision = "0005_starter_recipes_author"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.add_column(
        "users",
        sa.Column("default_servings", sa.Integer(), nullable=False, server_default=sa.text("4")),
    )
    op.add_column(
        "users",
        sa.Column("allergens", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column("users", sa.Column("custom_allergens_text", sa.Text(), nullable=True))

    # --- recipes ---
    op.add_column("recipes", sa.Column("prep_time_minutes", sa.Integer(), nullable=True))
    op.add_column("recipes", sa.Column("cook_time_minutes", sa.Integer(), nullable=True))
    op.add_column("recipes", sa.Column("user_rating", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_recipes_user_rating_1_5",
        "recipes",
        "(user_rating IS NULL) OR (user_rating >= 1 AND user_rating <= 5)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_recipes_user_rating_1_5", "recipes", type_="check")
    op.drop_column("recipes", "user_rating")
    op.drop_column("recipes", "cook_time_minutes")
    op.drop_column("recipes", "prep_time_minutes")

    op.drop_column("users", "custom_allergens_text")
    op.drop_column("users", "allergens")
    op.drop_column("users", "default_servings")
