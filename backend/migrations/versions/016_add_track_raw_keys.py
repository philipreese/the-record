"""Add track_raw_keys table.

Maps raw imported listen identities (artist_raw_folded, title_raw_folded) to
a canonical_tracks row. This is the fan-out join table: when a user saves a
track correction, one canonical_tracks row is created and one track_raw_keys
row is inserted per distinct raw identity that currently resolves to that track.

The UNIQUE constraint on (artist_raw_folded, title_raw_folded) enforces that
each raw key maps to at most one canonical track.

Revision ID: 016
Revises: 015
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "track_raw_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("canonical_track_id", sa.Integer(), nullable=False),
        sa.Column("artist_raw_folded", sa.Text(), nullable=False),
        sa.Column("title_raw_folded", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "artist_raw_folded", "title_raw_folded", name="uq_track_raw_keys_identity"
        ),
    )
    op.create_index(
        "idx_track_raw_keys_identity",
        "track_raw_keys",
        ["artist_raw_folded", "title_raw_folded"],
    )
    op.create_index(
        "idx_track_raw_keys_track_id",
        "track_raw_keys",
        ["canonical_track_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_track_raw_keys_track_id", table_name="track_raw_keys")
    op.drop_index("idx_track_raw_keys_identity", table_name="track_raw_keys")
    op.drop_table("track_raw_keys")
