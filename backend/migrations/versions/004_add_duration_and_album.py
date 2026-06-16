"""Add duration_secs and album columns to listens table.

Revision ID: 004
Revises: 003
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listens", sa.Column("duration_secs", sa.Integer(), nullable=True))
    op.add_column("listens", sa.Column("album", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("listens", "duration_secs")
    op.drop_column("listens", "album")
