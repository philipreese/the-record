"""Add expression index on (LOWER(artist), LOWER(title), unix_ts) to speed up dedup.

The deduplication query joins listens to itself on LOWER(artist) = LOWER(b.artist)
and LOWER(title) = LOWER(b.title). Without an expression index, SQLite falls back to
a full-table scan for every row, making it O(n^2) on large tables.

Revision ID: 006
Revises: 005
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_listens_lower_dedup"
        " ON listens (LOWER(artist), LOWER(title), unix_ts)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_listens_lower_dedup")
