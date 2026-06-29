"""Extend corrected_listens view with correction status columns.

Adds has_listen_correction (bool), has_track_correction (bool), and
track_id (nullable int) to the view so list queries surface correction
status without an extra round-trip to the DB.

Revision ID: 018
Revises: 017
Create Date: 2026-06-28
"""
from typing import Sequence, Union

from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
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
    COALESCE(lc.recording_mbid,ct.recording_mbid,l.recording_mbid)AS recording_mbid,
    (lc.listen_id IS NOT NULL)                                    AS has_listen_correction,
    (trk.canonical_track_id IS NOT NULL)                          AS has_track_correction,
    trk.canonical_track_id                                        AS track_id
FROM listens l
LEFT JOIN listen_corrections lc ON lc.listen_id = l.id
LEFT JOIN track_raw_keys trk    ON trk.artist_raw_folded = l.artist_raw_folded
                                AND trk.title_raw_folded  = l.title_raw_folded
LEFT JOIN canonical_tracks ct   ON ct.id = trk.canonical_track_id
"""


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS corrected_listens")
    op.execute(_VIEW_DDL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS corrected_listens")
    # Restore the 017 version without boolean flags
    op.execute("""\
CREATE VIEW corrected_listens AS
SELECT
    l.id, l.unix_ts, l.source, l.artist_raw_folded, l.title_raw_folded,
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
""")
