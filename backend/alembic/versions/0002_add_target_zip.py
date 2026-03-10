"""add target_zip to users

Revision ID: 0002_add_target_zip
Revises: 0001_create_tables
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_target_zip"
down_revision = "0001_create_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("target_zip", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "target_zip")

