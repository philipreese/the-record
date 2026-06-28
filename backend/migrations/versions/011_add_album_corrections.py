"""Add album_corrections table for normalizing scrobbler metadata.

Scrobblers submit album names verbatim from source metadata, which can differ
from the canonical name or be outright wrong. This table lets us map wrong
album names to correct ones and re-apply after mirror syncs.

Revision ID: 011
Revises: 010
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "album_corrections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("wrong_album", sa.Text(), nullable=False, unique=True),
        sa.Column("correct_album", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("album_corrections")
