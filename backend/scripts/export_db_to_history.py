"""
Export history.db to merged_history.json.

Run this after all DB cleanup is complete and before the ListenBrainz steps.
It makes merged_history.json an exact mirror of the DB so that
delete_listenbrainz.py knows which entries to remove from LB (anything
submitted previously that is no longer in the DB).

Usage:
  python export_db_to_history.py           # dry run — shows count only
  python export_db_to_history.py --confirm  # write merged_history.json
"""

import json
import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from app.db import get_session, Listen, JSON_PATH
from sqlalchemy import select

OUTPUT_FILE = JSON_PATH  # backend/merged_history.json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="Write the file (default is dry run)")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output path (default: merged_history.json)")
    args = parser.parse_args()

    session = get_session()
    try:
        rows = session.execute(
            select(Listen).order_by(Listen.unix_ts)
        ).scalars().all()
    finally:
        session.close()

    history = [
        {
            "unix_ts": r.unix_ts,
            "artist": r.artist,
            "title": r.title,
            "source": r.source,
        }
        for r in rows
    ]

    print(f"{'=== DRY RUN ===' if not args.confirm else '=== WRITING FILE ==='}")
    print(f"\nDB contains {len(history):,} listen rows.")
    print(f"Output: {args.output}")

    if not args.confirm:
        print("\nDry run — pass --confirm to write merged_history.json.")
        return

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

    print(f"\nWrote {len(history):,} entries to {args.output}.")
    print("Run delete_listenbrainz.py next.")


if __name__ == "__main__":
    main()
