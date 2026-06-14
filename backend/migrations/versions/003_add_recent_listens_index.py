"""Add composite index on (unix_ts, id) for cursor-based recent listens pagination.

The existing idx_listens_unix_ts single-column index doesn't keep the keyset
WHERE (unix_ts, id) < (before_ts, before_id) filter index-only as the table grows.
This composite index covers both the sort and the cursor predicate.

Revision ID: 003
Revises: 002
Create Date: 2026-06-14
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_listens_recent", "listens", ["unix_ts", "id"])


def downgrade() -> None:
    op.drop_index("idx_listens_recent", table_name="listens")
