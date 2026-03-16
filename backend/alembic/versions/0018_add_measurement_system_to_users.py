"""add measurement_system to users

Revision ID: 0019_measurement_system
Revises: 0018_user_filter_names
Create Date: 2026-03-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_measurement_system"
down_revision: Union[str, None] = "0018_user_filter_names"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "measurement_system",
            sa.String(length=16),
            nullable=False,
            server_default="metric",
        ),
    )
    op.alter_column("users", "measurement_system", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "measurement_system")

