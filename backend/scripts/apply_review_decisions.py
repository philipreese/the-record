"""
Apply decisions from failure_review.csv to history.db.

  delete — removes all listens for that specific (artist, title) pair
  fix    — renames (artist, title) to (fix_artist, fix_title); writes
           fix_retry.json so you can re-run backfill on corrected entries
  keep   — no action

Usage:
  python apply_review_decisions.py              # dry run
  python apply_review_decisions.py --confirm    # apply changes
  python apply_review_decisions.py --csv path/to/failure_review.csv
"""

import csv
import json
import os
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from app.db import get_session, Listen
from app.repository import deduplicate_listens
from sqlalchemy import delete as sa_delete, update, and_

CSV_FILE = os.path.join(SCRIPT_DIR, "failure_review.csv")
FIX_RETRY_FILE = os.path.join(SCRIPT_DIR, "fix_retry.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=CSV_FILE)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(args.csv, newline="", encoding=enc) as f:
                rows = list(csv.DictReader(f))
            break
        except UnicodeDecodeError:
            continue
    else:
        print("ERROR: Could not decode CSV.")
        sys.exit(1)

    to_delete: list[tuple[str, str]] = []
    to_fix: list[tuple[str, str, str, str]] = []  # (old_artist, old_title, new_artist, new_title)
    to_keep: list[tuple[str, str]] = []
    errors: list[str] = []

    for i, r in enumerate(rows, start=2):  # row 2 = first data row (after header)
        decision = r["decision"].strip().lower()
        artist = r["artist"].strip()
        title = r["title"].strip()

        if decision == "delete":
            to_delete.append((artist, title))
        elif decision == "fix":
            new_artist = r.get("fix_artist", "").strip() or artist
            new_title = r.get("fix_title", "").strip() or title
            if new_artist == artist and new_title == title:
                errors.append(f"Row {i}: decision=fix but fix_artist/fix_title are blank — {artist!r}")
            else:
                to_fix.append((artist, title, new_artist, new_title))
        elif decision in ("keep", ""):
            to_keep.append((artist, title))
        else:
            errors.append(f"Row {i}: unknown decision {r['decision']!r} for {artist!r} / {title!r}")

    print(f"{'=== DRY RUN ===' if not args.confirm else '=== APPLYING CHANGES ==='}\n")

    if errors:
        print("ERRORS (fix before running --confirm):")
        for e in errors:
            print(f"  {e}")
        print()

    print(f"delete: {len(to_delete)} tracks")
    for a, t in to_delete:
        print(f"  {a!r} / {t!r}")

    print(f"\nfix:    {len(to_fix)} tracks")
    for old_a, old_t, new_a, new_t in to_fix:
        print(f"  {old_a!r} / {old_t!r}")
        print(f"    -> {new_a!r} / {new_t!r}")

    print(f"\nkeep:   {len(to_keep)} tracks (no action)")

    if not args.confirm:
        print("\nDry run — pass --confirm to apply.")
        return

    if errors:
        print("\nAborting due to errors above.")
        sys.exit(1)

    session = get_session()
    total_deleted = 0
    total_fixed = 0

    try:
        for artist, title in to_delete:
            result = session.execute(
                sa_delete(Listen).where(
                    and_(Listen.artist == artist, Listen.title == title)
                )
            )
            total_deleted += result.rowcount

        for old_artist, old_title, new_artist, new_title in to_fix:
            result = session.execute(
                update(Listen)
                .where(and_(Listen.artist == old_artist, Listen.title == old_title))
                .values(artist=new_artist, title=new_title)
            )
            total_fixed += result.rowcount

        session.commit()
        print(f"\nDeleted {total_deleted} listen row(s).")
        print(f"Fixed   {total_fixed} listen row(s).")

        dupes = deduplicate_listens()
        print(f"Deduplicated {dupes} duplicate row(s).")

    finally:
        session.close()

    if to_fix:
        retry = [{"artist": new_a, "title": new_t} for _, _, new_a, new_t in to_fix]
        with open(FIX_RETRY_FILE, "w", encoding="utf-8") as f:
            json.dump(retry, f, indent=2, ensure_ascii=False)
        print(f"\nWrote {len(retry)} corrected entries to {FIX_RETRY_FILE}.")
        print("Re-run backfill_metadata.py to fill metadata for corrected tracks.")


if __name__ == "__main__":
    main()
