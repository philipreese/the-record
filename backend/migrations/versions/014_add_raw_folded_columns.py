"""Add artist_raw_folded and title_raw_folded to listens.

These columns store the Python .casefold().strip() of the original LB-imported
artist and title values. They are set at INSERT time and never updated — even
when apply_artist_corrections() rewrites listens.artist. This immutability
makes them safe JOIN keys for track_raw_keys (migration 016): a batch artist
correction changing listens.artist cannot orphan existing track corrections.

SQL lower() is ASCII-only, so the backfill is done in Python.

Revision ID: 014
Revises: 013
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listens", sa.Column("artist_raw_folded", sa.Text(), nullable=True))
    op.add_column("listens", sa.Column("title_raw_folded", sa.Text(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, artist, title FROM listens")).fetchall()
    
    updates = []
    for row in rows:
        af = (row.artist or "").casefold().strip()
        tf = (row.title or "").casefold().strip()
        updates.append({"af": af, "tf": tf, "id": row.id})
        
    if updates:
        # Execute in chunks to avoid memory/parameter limits on some databases
        chunk_size = 10000
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i:i + chunk_size]
            bind.execute(
                sa.text(
                    "UPDATE listens SET artist_raw_folded = :af, title_raw_folded = :tf WHERE id = :id"
                ),
                chunk,
            )

    op.create_index(
        "idx_listens_raw_folded", "listens", ["artist_raw_folded", "title_raw_folded"]
    )


def downgrade() -> None:
    op.drop_index("idx_listens_raw_folded", table_name="listens")
    op.drop_column("listens", "title_raw_folded")
    op.drop_column("listens", "artist_raw_folded")
