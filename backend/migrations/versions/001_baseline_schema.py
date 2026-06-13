"""Baseline schema: listens table with initial indexes.

For databases created before Alembic was adopted, stamp this revision
rather than running the upgrade:

    alembic stamp 001

Revision ID: 001
Revises:
Create Date: 2026-06-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("artist", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("unix_ts", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_listens_unix_ts", "listens", ["unix_ts"])
    op.create_index("idx_listens_artist", "listens", ["artist"])


def downgrade() -> None:
    op.drop_index("idx_listens_artist", table_name="listens")
    op.drop_index("idx_listens_unix_ts", table_name="listens")
    op.drop_table("listens")
