"""Add corrected_listens view.

Layered read model that applies user corrections on top of raw imported data:

  listen_corrections (per-listen)  >  canonical_tracks (per-track)  >  listens (raw)

The view is a simple double LEFT JOIN with no subqueries or GROUP BY, so the
query planner can push outer WHERE / ORDER BY clauses directly into the scan.

Writes still target listens directly. All user-visible read queries should
select from corrected_listens instead of listens.

Revision ID: 017
Revises: 016
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VIEW_DDL = """\
CREATE VIEW corrected_listens AS
SELECT
    l.id,
    l.unix_ts,
    l.source,
    l.artist_raw_folded,
    l.title_raw_folded,
    COALESCE(lc.artist,        ct.artist,        l.artist)        AS artist,
    COALESCE(lc.title,         ct.title,         l.title)         AS title,
    COALESCE(lc.album,         ct.album,         l.album)         AS album,
    COALESCE(lc.duration_secs, ct.duration_secs, l.duration_secs) AS duration_secs,
    COALESCE(lc.recording_mbid,ct.recording_mbid,l.recording_mbid)AS recording_mbid
FROM listens l
LEFT JOIN listen_corrections lc ON lc.listen_id = l.id
LEFT JOIN track_raw_keys trk    ON trk.artist_raw_folded = l.artist_raw_folded
                                AND trk.title_raw_folded  = l.title_raw_folded
LEFT JOIN canonical_tracks ct   ON ct.id = trk.canonical_track_id
"""


def upgrade() -> None:
    op.execute(_VIEW_DDL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS corrected_listens")
