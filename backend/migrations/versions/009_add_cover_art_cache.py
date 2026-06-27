"""Add cover_art_cache table for persistent iTunes art resolution.

Art URLs resolved via iTunes are stored here so server restarts don't discard
all resolved art and re-hit the API rate limit on every boot.

Revision ID: 009
Revises: 008
Create Date: 2026-06-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cover_art_cache",
        sa.Column("artist_folded", sa.String(), nullable=False),
        sa.Column("title_folded", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("artist_folded", "title_folded"),
    )


def downgrade() -> None:
    op.drop_table("cover_art_cache")
