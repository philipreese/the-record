"""
Mirror the local SQLite database (history.db) to the production PostgreSQL
database, column-for-column.

WHY THIS EXISTS
---------------
merged_history.json / bootstrap only carry artist/title/unix_ts/source and drop
album + duration_secs, and bootstrap is a no-op once prod is non-empty. After a
local data-cleaning effort we need prod to become an exact copy of the cleaned
DB *including* album and duration metadata, so this does a direct DB->DB copy of
all columns.

WHAT IT DOES
------------
  1. Always writes a logical backup of the CURRENT prod `listens` table (all
     columns, including id) to backend/backups/prod_listens_backup_<ts>.json.
  2. Reports source (local SQLite) and destination (prod) row counts.
  3. With --confirm: inside a single transaction, DELETEs every prod row and
     bulk-inserts the local rows (id omitted so the sequence regenerates).
     The delete+insert is atomic: if the insert fails, the delete rolls back
     and prod is left untouched.

SAFETY
------
  - Source is ALWAYS the local sqlite history.db, opened explicitly. It never
    reads through DATABASE_URL (which points at prod).
  - Destination comes from DATABASE_URL in the project .env.
  - Run it while no ListenBrainz sync is active.

Usage:
  python backend/scripts/mirror_to_prod.py            # dry run + backup
  python backend/scripts/mirror_to_prod.py --confirm  # backup + mirror
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.db import (  # ORM model / table definitions
    Listen, CoverArtCache, ListenCorrection, CanonicalTrack, TrackRawKey,
)

load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

COLUMNS = ["id", "artist", "title", "unix_ts", "source", "duration_secs", "album",
           "artist_raw_folded", "title_raw_folded"]
# Columns copied into prod (id omitted so the autoincrement sequence regenerates)
COPY_COLUMNS = ["artist", "title", "unix_ts", "source", "duration_secs", "album",
                "artist_raw_folded", "title_raw_folded"]

COVER_ART_COLUMNS = ["artist_folded", "title_folded", "url"]

# listen_corrections: omit id (nothing references it; sequence regenerates)
LC_COPY_COLUMNS = ["listen_id", "artist", "title", "album", "duration_secs", "recording_mbid",
                   "corrected_at"]
# canonical_tracks + track_raw_keys: include id so cross-table reference stays consistent
CT_COPY_COLUMNS = ["id", "artist", "title", "album", "duration_secs", "recording_mbid",
                   "corrected_at"]
TRK_COPY_COLUMNS = ["id", "canonical_track_id", "artist_raw_folded", "title_raw_folded"]

BACKUP_DIR = os.path.join(BACKEND_DIR, "backups")


def normalize_pg_url(url: str) -> str:
    """Match app.db.get_engine: force the psycopg (v3) dialect."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def make_source_engine():
    db_path = os.environ.get(
        "DATABASE_PATH", os.path.join(BACKEND_DIR, "history.db")
    )
    abs_path = os.path.abspath(db_path).replace("\\", "/")
    if not os.path.exists(abs_path):
        sys.exit(f"ERROR: local source DB not found at {abs_path}")
    return create_engine(
        f"sqlite:///{abs_path}", connect_args={"check_same_thread": False}
    )


def make_dest_engine():
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.exit("ERROR: DATABASE_URL is not set (expected prod postgres in .env).")
    url = normalize_pg_url(raw)
    if not url.startswith("postgresql+psycopg://"):
        sys.exit(f"ERROR: DATABASE_URL is not a postgres URL (got scheme '{url.split('://')[0]}').")
    return create_engine(url, pool_pre_ping=True)


def row_to_dict(row) -> dict:
    return {c: getattr(row, c) for c in COLUMNS}


def backup_dest(DestSession) -> tuple[str, int]:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(BACKUP_DIR, f"prod_listens_backup_{ts}.json")
    session = DestSession()
    try:
        rows = session.execute(select(Listen).order_by(Listen.id)).scalars().all()
        data = [row_to_dict(r) for r in rows]
    finally:
        session.close()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path, len(data)


def count(SessionFactory) -> int:
    session = SessionFactory()
    try:
        return session.execute(select(func.count(Listen.id))).scalar() or 0
    finally:
        session.close()


def count_cover_art(SessionFactory) -> int:
    session = SessionFactory()
    try:
        return session.execute(select(func.count(CoverArtCache.artist_folded))).scalar() or 0
    finally:
        session.close()


def backup_cover_art(DestSession) -> tuple[str, int]:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(BACKUP_DIR, f"prod_cover_art_backup_{ts}.json")
    session = DestSession()
    try:
        rows = session.execute(select(CoverArtCache)).scalars().all()
        data = [{c: getattr(r, c) for c in COVER_ART_COLUMNS} for r in rows]
    finally:
        session.close()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path, len(data)


def count_table(SessionFactory, model) -> int:
    session = SessionFactory()
    try:
        return session.execute(select(func.count()).select_from(model)).scalar() or 0
    finally:
        session.close()


def _reset_pg_sequence(session, table_name: str, id_col: str = "id") -> None:
    """Advance the Postgres sequence to max(id) so next INSERT doesn't conflict."""
    session.execute(
        __import__("sqlalchemy").text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', '{id_col}'), "
            f"COALESCE((SELECT MAX({id_col}) FROM {table_name}), 0))"
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Perform the destructive truncate + insert (default is a dry run).",
    )
    args = parser.parse_args()

    source_engine = make_source_engine()
    dest_engine = make_dest_engine()
    SourceSession = sessionmaker(bind=source_engine)
    DestSession = sessionmaker(bind=dest_engine)

    src_count = count(SourceSession)
    dst_count = count(DestSession)
    src_art_count = count_cover_art(SourceSession)
    dst_art_count = count_cover_art(DestSession)
    src_lc_count = count_table(SourceSession, ListenCorrection)
    dst_lc_count = count_table(DestSession, ListenCorrection)
    src_ct_count = count_table(SourceSession, CanonicalTrack)
    dst_ct_count = count_table(DestSession, CanonicalTrack)
    src_trk_count = count_table(SourceSession, TrackRawKey)
    dst_trk_count = count_table(DestSession, TrackRawKey)

    # Show a sanitized destination host so the operator can confirm the target
    # without printing credentials.
    dest_host = str(dest_engine.url.host)
    dest_db = str(dest_engine.url.database)

    print("=== MIRROR LOCAL -> PROD ===")
    print(f"Source (sqlite):  listens={src_count:,}  cover_art={src_art_count:,}  "
          f"listen_corrections={src_lc_count:,}  canonical_tracks={src_ct_count:,}  "
          f"track_raw_keys={src_trk_count:,}")
    print(f"Dest   (postgres {dest_host}/{dest_db}): listens={dst_count:,}  cover_art={dst_art_count:,}  "
          f"listen_corrections={dst_lc_count:,}  canonical_tracks={dst_ct_count:,}  "
          f"track_raw_keys={dst_trk_count:,}")

    print("\nBacking up current prod listens table...")
    backup_path, backup_count = backup_dest(DestSession)
    print(f"  Wrote {backup_count:,} rows to {backup_path}")

    print("Backing up current prod cover_art_cache table...")
    art_backup_path, art_backup_count = backup_cover_art(DestSession)
    print(f"  Wrote {art_backup_count:,} rows to {art_backup_path}")

    if not args.confirm:
        print("\n=== DRY RUN ===")
        print(f"Would DELETE {dst_count:,} prod listens and INSERT {src_count:,} from local.")
        print(f"Would DELETE {dst_art_count:,} prod cover_art_cache rows and INSERT {src_art_count:,} from local.")
        print(f"Would DELETE {dst_lc_count:,} prod listen_corrections and INSERT {src_lc_count:,} from local.")
        print(f"Would DELETE {dst_ct_count:,} prod canonical_tracks and INSERT {src_ct_count:,} from local.")
        print(f"Would DELETE {dst_trk_count:,} prod track_raw_keys and INSERT {src_trk_count:,} from local.")
        print("Re-run with --confirm to apply.")
        return

    print("\n=== APPLYING (truncate + insert, single transaction) ===")

    # Read all source rows up front.
    s = SourceSession()
    try:
        src_rows = s.execute(select(Listen).order_by(Listen.unix_ts)).scalars().all()
        listen_mappings = [{c: getattr(r, c) for c in COPY_COLUMNS} for r in src_rows]
        art_rows = s.execute(select(CoverArtCache)).scalars().all()
        art_mappings = [{c: getattr(r, c) for c in COVER_ART_COLUMNS} for r in art_rows]
        lc_rows = s.execute(select(ListenCorrection)).scalars().all()
        lc_mappings = [{c: getattr(r, c) for c in LC_COPY_COLUMNS} for r in lc_rows]
        ct_rows = s.execute(select(CanonicalTrack)).scalars().all()
        ct_mappings = [{c: getattr(r, c) for c in CT_COPY_COLUMNS} for r in ct_rows]
        trk_rows = s.execute(select(TrackRawKey)).scalars().all()
        trk_mappings = [{c: getattr(r, c) for c in TRK_COPY_COLUMNS} for r in trk_rows]
    finally:
        s.close()

    from sqlalchemy import text as _text

    d = DestSession()
    try:
        # Correction tables first (FK order: delete dependents before parents)
        d.execute(TrackRawKey.__table__.delete())
        d.execute(ListenCorrection.__table__.delete())
        d.execute(CanonicalTrack.__table__.delete())
        # Main data tables
        d.execute(Listen.__table__.delete())
        d.execute(CoverArtCache.__table__.delete())

        d.bulk_insert_mappings(Listen, listen_mappings)
        d.bulk_insert_mappings(CoverArtCache, art_mappings)
        if lc_mappings:
            d.bulk_insert_mappings(ListenCorrection, lc_mappings)
        if ct_mappings:
            d.bulk_insert_mappings(CanonicalTrack, ct_mappings)
            _reset_pg_sequence(d, "canonical_tracks")
        if trk_mappings:
            d.bulk_insert_mappings(TrackRawKey, trk_mappings)
            _reset_pg_sequence(d, "track_raw_keys")

        # Orphan cleanup: listen_corrections rows whose listen was deleted during mirror sync
        orphans = d.execute(
            _text(
                "DELETE FROM listen_corrections "
                "WHERE listen_id NOT IN (SELECT id FROM listens)"
            )
        ).rowcount
        if orphans:
            print(f"  Cleaned up {orphans} orphaned listen_corrections row(s).")

        d.commit()
    except Exception:
        d.rollback()
        print("ERROR: mirror failed and was rolled back. Prod is unchanged.")
        raise
    finally:
        d.close()

    final = count(DestSession)
    final_art = count_cover_art(DestSession)
    final_lc = count_table(DestSession, ListenCorrection)
    final_ct = count_table(DestSession, CanonicalTrack)
    final_trk = count_table(DestSession, TrackRawKey)
    print(f"Done. Prod listens: {final:,} (source: {src_count:,}).")
    print(f"Done. Prod cover_art_cache: {final_art:,} (source: {src_art_count:,}).")
    print(f"Done. Prod listen_corrections: {final_lc:,} (source: {src_lc_count:,}).")
    print(f"Done. Prod canonical_tracks: {final_ct:,} (source: {src_ct_count:,}).")
    print(f"Done. Prod track_raw_keys: {final_trk:,} (source: {src_trk_count:,}).")
    if final != src_count:
        print("WARNING: listens count does not match source!")
    if final_art != src_art_count:
        print("WARNING: cover_art_cache count does not match source!")
    print(f"Listens backup:    {backup_path}")
    print(f"Cover art backup:  {art_backup_path}")


if __name__ == "__main__":
    main()
