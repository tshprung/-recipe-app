"""Clear image_url from starter recipes (no longer use static images).

Revision ID: 0016_starter_no_images
Revises: 0015_recipe_collections
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0016_starter_no_images"
down_revision = "0015_recipe_collections"
branch_labels = None
depends_on = None

# URLs previously used as static starter images; clear them so starters show no image.
_STARTER_IMAGE_URLS = (
    "https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=600&q=70",
    "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=70",
    "https://images.unsplash.com/photo-1565958011703-44f9829ba187?auto=format&fit=crop&w=600&q=70",
)


def upgrade() -> None:
    conn = op.get_bind()
    for url in _STARTER_IMAGE_URLS:
        conn.execute(sa.text("UPDATE recipes SET image_url = NULL WHERE image_url = :u"), {"u": url})


def downgrade() -> None:
    # No way to restore previous image_url values; leave as no-op.
    pass
