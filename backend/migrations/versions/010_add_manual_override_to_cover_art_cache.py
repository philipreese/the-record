"""Add manual_override flag to cover_art_cache.

When True, the background art resolver skips this entry so manually set
cover art URLs are never overwritten by automatic resolution.

Revision ID: 010
Revises: 009
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cover_art_cache",
        sa.Column("manual_override", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("cover_art_cache", "manual_override")
