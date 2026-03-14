"""add recipe.trial_session_id and make user_id nullable for trial recipes

Revision ID: 0012_trial_session
Revises: 0011_trial_sessions
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa

revision = "0012_trial_session"
down_revision = "0011_trial_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite does not support ALTER ADD CONSTRAINT; use batch_alter_table.
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("recipes") as batch_op:
            batch_op.add_column(
                sa.Column("trial_session_id", sa.Integer(), nullable=True),
            )
            batch_op.create_foreign_key(
                "fk_recipes_trial_session_id",
                "trial_sessions",
                ["trial_session_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(
                "ix_recipes_trial_session_id",
                ["trial_session_id"],
            )
            batch_op.alter_column(
                "user_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
    else:
        op.add_column(
            "recipes",
            sa.Column("trial_session_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_recipes_trial_session_id",
            "recipes",
            "trial_sessions",
            ["trial_session_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            "ix_recipes_trial_session_id",
            "recipes",
            ["trial_session_id"],
        )
        op.alter_column(
            "recipes",
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if is_sqlite:
        with op.batch_alter_table("recipes") as batch_op:
            batch_op.alter_column(
                "user_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
            batch_op.drop_index("ix_recipes_trial_session_id")
            batch_op.drop_constraint("fk_recipes_trial_session_id", type_="foreignkey")
            batch_op.drop_column("trial_session_id")
    else:
        op.alter_column(
            "recipes",
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        op.drop_index("ix_recipes_trial_session_id", table_name="recipes")
        op.drop_constraint("fk_recipes_trial_session_id", "recipes", type_="foreignkey")
        op.drop_column("recipes", "trial_session_id")
