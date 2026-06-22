"""Add recording_mbid column for canonical track identity.

Multi-artist tracks (e.g. "Beartooth & Hardy" vs "Beartooth") are stored under
inconsistent artist-credit strings and counted separately. The MusicBrainz
Recording ID, provided by ListenBrainz in
track_metadata.additional_info.recording_mbid, gives a stable identity across
those variants. Nullable: pre-LB imports (e.g. YT Music) won't have one until a
Full Reconstruction sync backfills it.

Revision ID: 007
Revises: 006
Create Date: 2026-06-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listens", sa.Column("recording_mbid", sa.Text(), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_listens_recording_mbid"
        " ON listens (recording_mbid)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_listens_recording_mbid")
    op.drop_column("listens", "recording_mbid")
