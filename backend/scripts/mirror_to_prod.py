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

from app.db import Listen  # ORM model / table definition

load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

COLUMNS = ["id", "artist", "title", "unix_ts", "source", "duration_secs", "album"]
# Columns copied into prod (id omitted so the autoincrement sequence regenerates)
COPY_COLUMNS = ["artist", "title", "unix_ts", "source", "duration_secs", "album"]

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

    # Show a sanitized destination host so the operator can confirm the target
    # without printing credentials.
    dest_host = str(dest_engine.url.host)
    dest_db = str(dest_engine.url.database)

    print("=== MIRROR LOCAL -> PROD ===")
    print(f"Source (sqlite history.db): {src_count:,} rows")
    print(f"Dest   (postgres {dest_host}/{dest_db}): {dst_count:,} rows")

    print("\nBacking up current prod listens table...")
    backup_path, backup_count = backup_dest(DestSession)
    print(f"  Wrote {backup_count:,} rows to {backup_path}")

    if not args.confirm:
        print("\n=== DRY RUN ===")
        print(f"Would DELETE {dst_count:,} prod rows and INSERT {src_count:,} from local.")
        print("Re-run with --confirm to apply.")
        return

    print("\n=== APPLYING (truncate + insert, single transaction) ===")
    # Read all source rows up front.
    s = SourceSession()
    try:
        src_rows = s.execute(select(Listen).order_by(Listen.unix_ts)).scalars().all()
        mappings = [
            {c: getattr(r, c) for c in COPY_COLUMNS} for r in src_rows
        ]
    finally:
        s.close()

    d = DestSession()
    try:
        d.execute(Listen.__table__.delete())
        d.bulk_insert_mappings(Listen, mappings)
        d.commit()
    except Exception:
        d.rollback()
        print("ERROR: mirror failed and was rolled back. Prod is unchanged.")
        raise
    finally:
        d.close()

    final = count(DestSession)
    print(f"Done. Prod now has {final:,} rows (source had {src_count:,}).")
    if final != src_count:
        print("WARNING: final count does not match source count!")
    print(f"Backup of the previous prod state: {backup_path}")


if __name__ == "__main__":
    main()
