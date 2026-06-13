"""Add composite dedup index on (artist, title, unix_ts).

Supports the post-sync dedup self-join query that removes duplicate listens
with the same artist, title, and timestamp across sync sessions.

Revision ID: 002
Revises: 001
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_listens_dedup", "listens", ["artist", "title", "unix_ts"])


def downgrade() -> None:
    op.drop_index("idx_listens_dedup", table_name="listens")
