"""Add original_url to cover_art_cache.

Stores the pre-override cover art URL so the correction drawer can show
what art was there before a manual override and offer a revert option.

Backfill: rows where manual_override=False have their current url set as
original_url (the 17-hour pre-fetch result IS the original). Rows that were
already manually overridden keep original_url=NULL — a separate script
(scripts/backfill_original_cover_art.py) re-fetches those.

Revision ID: 019
Revises: 018
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cover_art_cache", sa.Column("original_url", sa.Text(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE cover_art_cache SET original_url = url WHERE NOT manual_override"))


def downgrade() -> None:
    op.drop_column("cover_art_cache", "original_url")
