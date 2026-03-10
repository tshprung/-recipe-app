"""create tables

Revision ID: 0001_create_tables
Revises: 
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("transformations_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transformations_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_token", sa.String(length=255), nullable=True),
        sa.Column("verification_token_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("account_tier", sa.String(length=50), nullable=False, server_default="free"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lockout_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ui_language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("target_language", sa.String(length=10), nullable=False, server_default="pl"),
        sa.Column("target_country", sa.String(length=10), nullable=False, server_default="PL"),
        sa.Column("target_city", sa.String(length=100), nullable=False, server_default="Wrocław"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title_pl", sa.String(length=500), nullable=False),
        sa.Column("title_original", sa.String(length=500), nullable=False),
        sa.Column("ingredients_pl", sa.JSON(), nullable=False),
        sa.Column("ingredients_original", sa.JSON(), nullable=False),
        sa.Column("steps_pl", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("substitutions", sa.JSON(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(length=10), nullable=True),
        sa.Column("target_language", sa.String(length=10), nullable=False),
        sa.Column("target_country", sa.String(length=10), nullable=False),
        sa.Column("target_city", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recipes_id", "recipes", ["id"])
    op.create_index("ix_recipes_user_id", "recipes", ["user_id"])

    op.create_table(
        "recipe_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_type", sa.String(length=50), nullable=False),
        sa.Column("title_pl", sa.String(length=500), nullable=False),
        sa.Column("ingredients_pl", sa.JSON(), nullable=False),
        sa.Column("steps_pl", sa.JSON(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recipe_variants_id", "recipe_variants", ["id"])
    op.create_index("ix_recipe_variants_recipe_id", "recipe_variants", ["recipe_id"])

    op.create_table(
        "shopping_list_recipes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shopping_list_recipes_id", "shopping_list_recipes", ["id"])
    op.create_index("ix_shopping_list_recipes_user_id", "shopping_list_recipes", ["user_id"])

    op.create_table(
        "ingredient_substitutions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ingredient_name", sa.String(length=255), nullable=False),
        sa.Column("source_country", sa.String(length=10), nullable=False),
        sa.Column("target_country", sa.String(length=10), nullable=False),
        sa.Column("substitution", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ingredient_substitutions_id", "ingredient_substitutions", ["id"])
    op.create_index("ix_ingredient_substitutions_ingredient_name", "ingredient_substitutions", ["ingredient_name"])


def downgrade() -> None:
    op.drop_index("ix_ingredient_substitutions_ingredient_name", table_name="ingredient_substitutions")
    op.drop_index("ix_ingredient_substitutions_id", table_name="ingredient_substitutions")
    op.drop_table("ingredient_substitutions")

    op.drop_index("ix_shopping_list_recipes_user_id", table_name="shopping_list_recipes")
    op.drop_index("ix_shopping_list_recipes_id", table_name="shopping_list_recipes")
    op.drop_table("shopping_list_recipes")

    op.drop_index("ix_recipe_variants_recipe_id", table_name="recipe_variants")
    op.drop_index("ix_recipe_variants_id", table_name="recipe_variants")
    op.drop_table("recipe_variants")

    op.drop_index("ix_recipes_user_id", table_name="recipes")
    op.drop_index("ix_recipes_id", table_name="recipes")
    op.drop_table("recipes")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

