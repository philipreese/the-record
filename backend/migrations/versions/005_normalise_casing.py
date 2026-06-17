"""Normalise artist/title casing across historical import data.

For each (unix_ts, lower(artist), lower(title)) group with casing variants,
pick the ListenBrainz-sourced row as canonical (MIN(id) among LB rows;
MIN(id) overall as fallback). Updates non-canonical rows to match, then
deletes exact duplicates that emerge after unification.

Revision ID: 005
Revises: 004
Create Date: 2026-06-17
"""
from collections import defaultdict
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    rows = bind.execute(
        text("SELECT id, unix_ts, artist, title, source FROM listens ORDER BY id")
    ).fetchall()

    # Group by case-folded (unix_ts, artist, title)
    groups: dict[tuple, list] = defaultdict(list)
    for row in rows:
        key = (row.unix_ts, row.artist.lower(), row.title.lower())
        groups[key].append(row)

    updated = 0
    for group_rows in groups.values():
        if len(group_rows) == 1:
            continue

        # Canonical: prefer LB-sourced row with lowest id; fallback to lowest id overall
        lb_rows = [r for r in group_rows if r.source and r.source.startswith("listenbrainz")]
        canonical = min(lb_rows, key=lambda r: r.id) if lb_rows else min(group_rows, key=lambda r: r.id)

        for r in group_rows:
            if r.id == canonical.id:
                continue
            if r.artist != canonical.artist or r.title != canonical.title:
                bind.execute(
                    text("UPDATE listens SET artist = :a, title = :t WHERE id = :id"),
                    {"a": canonical.artist, "t": canonical.title, "id": r.id},
                )
                updated += 1

    # After casing is unified, remove exact duplicates (same artist/title/unix_ts), keeping MIN(id)
    result = bind.execute(text("""
        DELETE FROM listens
        WHERE id IN (
            SELECT b.id
            FROM listens a
            JOIN listens b
              ON a.artist   = b.artist
             AND a.title    = b.title
             AND a.unix_ts  = b.unix_ts
             AND a.id < b.id
        )
    """))
    deleted = result.rowcount

    print(f"  Casing migration: {updated} row(s) recased, {deleted} exact duplicate(s) removed.")


def downgrade() -> None:
    # Casing normalisation is non-reversible — original values are not retained.
    pass
