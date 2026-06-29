"""Add canonical_tracks table.

canonical_tracks is the user-maintained canonical metadata for a logical track.
It is distinct from listens (imported play events) — not every track in listens
has a row here; only those the user has explicitly corrected.

recording_mbid has a partial unique constraint (excluding NULLs) so that once
an MBID is assigned to a logical track, no second canonical_tracks row can claim
the same MBID. This enforces the invariant:
  one recording MBID == one logical track.

When no MBID is available, artist+title is treated as the best available
approximation of logical track identity and multiple recordings of the same
title may be merged into one canonical_tracks row.

Revision ID: 015
Revises: 014
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canonical_tracks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("artist", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("album", sa.Text(), nullable=True),
        sa.Column("duration_secs", sa.Integer(), nullable=True),
        sa.Column("recording_mbid", sa.Text(), nullable=True, unique=True),
        sa.Column("corrected_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("canonical_tracks")
