"""Add listen_corrections table for per-listen metadata overrides.

Stores field-level corrections for individual listens. Applied after batch
corrections (artist_corrections, album_corrections) on each startup so
manual fixes survive redeployments and mirror syncs.

The unique constraint on (listen_id, field) means repeat corrections upsert
rather than append, keeping re_apply_listen_corrections O(n) over time.

Revision ID: 012
Revises: 011
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listen_corrections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("listen_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("corrected_value", sa.Text(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("lb_synced", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("listen_id", "field", name="uq_listen_corrections_listen_field"),
    )
    op.create_index("idx_listen_corrections_listen_id", "listen_corrections", ["listen_id"])


def downgrade() -> None:
    op.drop_index("idx_listen_corrections_listen_id", table_name="listen_corrections")
    op.drop_table("listen_corrections")
