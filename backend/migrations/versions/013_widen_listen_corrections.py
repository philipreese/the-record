"""Widen listen_corrections from EAV to per-field columns.

Migration 012 created an EAV table (listen_id, field, corrected_value). This
migration replaces it with a wide schema: one nullable column per correctable
field, one row per listen. The table was empty on both dev and prod at the
time of this migration.

Downgrade recreates the 012 EAV schema so the chain is reversible.

Revision ID: 013
Revises: 012
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_listen_corrections_listen_id", table_name="listen_corrections")
    op.drop_table("listen_corrections")

    op.create_table(
        "listen_corrections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("listen_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("album", sa.Text(), nullable=True),
        sa.Column("duration_secs", sa.Integer(), nullable=True),
        sa.Column("recording_mbid", sa.Text(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_listen_corrections_listen_id", "listen_corrections", ["listen_id"])


def downgrade() -> None:
    op.drop_index("idx_listen_corrections_listen_id", table_name="listen_corrections")
    op.drop_table("listen_corrections")

    # Recreate the EAV schema from migration 012
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
