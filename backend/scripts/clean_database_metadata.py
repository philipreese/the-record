"""
One-time script to clean artist/title fields in history.db and deduplicate.

IMPORTANT — run in this order to avoid sync.py overwriting local cleanup:
  1. Backup history.db
  2. merge_history.py       (regenerate clean merged_history.json)
  3. THIS SCRIPT            (clean + dedup local DB)
  4. delete_listenbrainz.py (remove messy scrobbles from LB)
  5. import_listenbrainz.py (re-import clean versions, updates checkpoint)
  6. sync.py is safe to run again

Usage:
  python clean_database_metadata.py          # dry run — prints counts only
  python clean_database_metadata.py --confirm  # applies changes
"""

import sys
import os
import argparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, BACKEND_DIR)

from app.db import get_session, Listen
from app.utils import clean_artist, clean_title, strip_artist_prefix
from app.repository import deduplicate_listens
from sqlalchemy import select


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="Apply changes (default is dry run)")
    args = parser.parse_args()

    session = get_session()
    try:
        rows = session.execute(select(Listen)).scalars().all()
        print(f"Total listens: {len(rows)}")

        dirty = []
        for row in rows:
            raw_artist = str(row.artist)
            raw_title = str(row.title)
            new_artist = clean_artist(raw_artist)
            new_title = clean_title(strip_artist_prefix(raw_title, raw_artist))
            if new_artist != row.artist or new_title != row.title:
                dirty.append((row, new_artist, new_title))

        print(f"Rows needing cleaning: {len(dirty)}")
        for row, new_artist, new_title in dirty[:20]:
            print(f"  [{row.id}] {row.artist!r} / {row.title!r}")
            print(f"       -> {new_artist!r} / {new_title!r}")
        if len(dirty) > 20:
            print(f"  ... and {len(dirty) - 20} more")

        if not args.confirm:
            print("\nDry run — pass --confirm to apply changes.")
            return

        for row, new_artist, new_title in dirty:
            row.artist = new_artist
            row.title = new_title
        session.commit()
        print(f"\nCleaned {len(dirty)} row(s).")

        deleted = deduplicate_listens()
        print(f"Deduplicated {deleted} duplicate row(s).")

    finally:
        session.close()


if __name__ == "__main__":
    main()
