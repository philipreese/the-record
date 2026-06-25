"""Add artist_corrections table for normalizing scrobbler metadata.

Scrobblers submit artist names verbatim from source metadata, which can differ
from the canonical MusicBrainz name (e.g. 'Invent Animate' vs 'Invent, Animate').
This table lets us map wrong names to correct ones and re-apply after mirror syncs.

Revision ID: 008
Revises: 007
Create Date: 2026-06-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artist_corrections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("wrong_name", sa.Text(), nullable=False, unique=True),
        sa.Column("correct_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("artist_corrections")
