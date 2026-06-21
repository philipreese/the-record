"""
Apply skipped_update / skipped entries from backfill_results.json to history.db.

After running backfill_metadata.py --reverify (without --confirm-updates),
use this script to review and apply proposed changes.

Workflow:
  1. Generate a review CSV:
       python apply_skipped_updates.py --generate-csv
  2. Open skipped_updates_review.csv in a spreadsheet editor.
     Set 'decision' for each row:
       accept  — apply MB's chosen_album / chosen_duration_secs as-is
       reject  — skip this track, leave DB unchanged
       fix     — use fix_* columns to override values (see below)
       delete  — remove ALL listens for this track from the DB
  3. Apply:
       python apply_skipped_updates.py --apply-csv        (dry run)
       python apply_skipped_updates.py --apply-csv --confirm

Fix column behaviour (decision=fix):
  fix_artist / fix_title  — rename the track in the DB; clears album &
                             duration so backfill can re-query MB with the
                             correct name. Combine with fix_album /
                             fix_duration_secs to skip the re-query.
  fix_album               — write this album directly (no rename needed)
  fix_duration_secs       — write this duration directly (no rename needed)
  Leave any fix_* column blank to leave that field untouched.

After applying, if any rows used fix_artist / fix_title, run:
  python backfill_metadata.py
to fill the corrected tracks (fast — only processes tracks missing data).

Quick bulk-apply (skips CSV, applies all skipped_update entries as accept):
  python apply_skipped_updates.py --confirm

Filter to one artist for spot-checking:
  python apply_skipped_updates.py --generate-csv --artist "Taylor Swift"
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
from sqlalchemy import update, and_, delete as sa_delete

RESULTS_FILE = os.path.join(SCRIPT_DIR, "backfill_results.json")
CSV_FILE = os.path.join(SCRIPT_DIR, "skipped_updates_review.csv")

VALID_DECISIONS = ("accept", "reject", "fix", "delete")

CSV_FIELDS = [
    "decision",
    "source",
    "artist",
    "title",
    "fix_artist",
    "fix_title",
    "existing_album",
    "chosen_album",
    "fix_album",
    "existing_duration_secs",
    "chosen_duration_secs",
    "fix_duration_secs",
    "chosen_score",
    "chosen_by",
    "raw_score",
    "clean_score",
    "chosen_recording",
    "cleaned_artist",
    "cleaned_title",
    "notes",
]


def _load_updates(results_path: str, artist_filter: str | None) -> list[dict]:
    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)
    updates = [r for r in results if r.get("action") in ("skipped_update", "skipped")]
    if artist_filter:
        updates = [r for r in updates if artist_filter.lower() in r["artist"].lower()]
    return updates


def _sort_key(r: dict) -> tuple:
    # Group: album corrections first, then fills, then duration-only, then low-confidence skipped
    action = r.get("action", "")
    if action == "skipped":
        group = 3
    elif r.get("existing_album") and r["existing_album"] != r.get("chosen_album"):
        group = 0  # album correction
    elif not r.get("existing_album") and r.get("chosen_album"):
        group = 1  # album fill
    else:
        group = 2  # duration-only
    return (group, r.get("chosen_score", 0.0), r["artist"].lower(), r["title"].lower())


def cmd_generate_csv(args: argparse.Namespace) -> None:
    updates = _load_updates(args.results, args.artist)
    updates.sort(key=_sort_key)

    rows = []
    for r in updates:
        rows.append({
            "decision": "accept",
            "source": r.get("action", ""),
            "artist": r["artist"],
            "title": r["title"],
            "fix_artist": "",
            "fix_title": "",
            "existing_album": r.get("existing_album") or "",
            "chosen_album": r.get("chosen_album") or "",
            "fix_album": "",
            "existing_duration_secs": r.get("existing_duration_secs") or "",
            "chosen_duration_secs": r.get("chosen_duration_secs") or "",
            "fix_duration_secs": "",
            "chosen_score": r.get("chosen_score", ""),
            "chosen_by": r.get("chosen_by") or "",
            "raw_score": r.get("raw_score", ""),
            "clean_score": r.get("clean_score", ""),
            "chosen_recording": r.get("chosen_recording") or "",
            "cleaned_artist": r.get("cleaned_artist") or "",
            "cleaned_title": r.get("cleaned_title") or "",
            "notes": "",
        })

    out_path = args.csv
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    skipped_update = [r for r in updates if r.get("action") == "skipped_update"]
    skipped_low = [r for r in updates if r.get("action") == "skipped"]
    album_corrections = sum(1 for r in skipped_update if r.get("existing_album") and r["existing_album"] != r.get("chosen_album"))
    album_fills = sum(1 for r in skipped_update if not r.get("existing_album") and r.get("chosen_album"))
    duration_only = len(skipped_update) - album_corrections - album_fills

    print(f"Wrote {len(rows)} entries to {out_path}")
    print(f"\nBreakdown (sorted: album corrections → fills → duration → low-confidence):")
    print(f"  skipped_update — album corrections (existing → different): {album_corrections}")
    print(f"  skipped_update — album fills (was null → new value):        {album_fills}")
    print(f"  skipped_update — duration-only changes:                     {duration_only}")
    print(f"  skipped        — low-confidence matches (< 0.8):            {len(skipped_low)}")
    print(f"\nColumns to focus on:")
    print(f"  source              — 'skipped_update' = high confidence; 'skipped' = low confidence")
    print(f"  existing_album vs chosen_album  — is MB's album better?")
    print(f"  chosen_recording    — does MB's track title match yours?")
    print(f"  chosen_score        — confidence of the MB match")
    print(f"  chosen_by           — 'raw' winning over 'clean' is a flag")
    print(f"\nDecision values:")
    print(f"  accept  — apply MB's chosen_album / chosen_duration_secs as-is")
    print(f"  reject  — skip this track, leave DB unchanged")
    print(f"  fix     — fill fix_artist/fix_title to rename the track (clears album/duration")
    print(f"            for backfill retry), and/or fill fix_album/fix_duration_secs directly")
    print(f"  delete  — remove ALL listens for this track from the DB")
    print(f"\nThen run: python apply_skipped_updates.py --apply-csv")


def _apply_entries(entries: list[dict], session) -> tuple[int, int]:
    """Apply accept/fix entries. Returns (updates_applied, renames_applied)."""
    updates_applied = 0
    renames_applied = 0

    for r in entries:
        decision = r.get("decision", "accept").strip().lower()
        artist = r["artist"]
        title = r["title"]

        fix_artist = (r.get("fix_artist") or "").strip()
        fix_title = (r.get("fix_title") or "").strip()
        fix_alb = (r.get("fix_album") or "").strip()
        fix_dur = (r.get("fix_duration_secs") or "").strip()

        if fix_artist or fix_title:
            new_artist = fix_artist or artist
            new_title = fix_title or title
            # Rename + clear album/duration for backfill retry
            rename_values: dict = {"artist": new_artist, "title": new_title, "album": None, "duration_secs": None}
            # If user also supplied fix_album/fix_duration, set those instead of clearing
            if fix_alb:
                rename_values["album"] = fix_alb
            if fix_dur:
                rename_values["duration_secs"] = int(fix_dur)
            session.execute(
                update(Listen)
                .where(and_(Listen.artist == artist, Listen.title == title))
                .values(**rename_values)
            )
            renames_applied += 1
        else:
            # No rename — just update album/duration
            values: dict = {}
            if decision == "fix":
                if fix_alb:
                    values["album"] = fix_alb
                if fix_dur:
                    values["duration_secs"] = int(fix_dur)
            else:
                # accept: use MB's chosen values
                chosen_dur = r.get("chosen_duration_secs")
                chosen_alb = r.get("chosen_album")
                if chosen_dur is not None and chosen_dur != "":
                    values["duration_secs"] = int(chosen_dur)
                if chosen_alb is not None and chosen_alb != "":
                    values["album"] = chosen_alb
            if values:
                session.execute(
                    update(Listen)
                    .where(and_(Listen.artist == artist, Listen.title == title))
                    .values(**values)
                )
                updates_applied += 1

    session.commit()
    return updates_applied, renames_applied


def cmd_apply_csv(args: argparse.Namespace) -> None:
    csv_path = args.csv
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        print("Run --generate-csv first.")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    accepted  = [r for r in rows if r.get("decision", "").strip().lower() == "accept"]
    fixed     = [r for r in rows if r.get("decision", "").strip().lower() == "fix"]
    rejected  = [r for r in rows if r.get("decision", "").strip().lower() == "reject"]
    to_delete = [r for r in rows if r.get("decision", "").strip().lower() == "delete"]
    other     = [r for r in rows if r.get("decision", "").strip().lower() not in VALID_DECISIONS]

    to_apply = accepted + fixed
    print(f"CSV: {len(rows)} total | {len(accepted)} accept | {len(fixed)} fix | {len(rejected)} reject | {len(to_delete)} delete | {len(other)} unrecognised")

    if other:
        print(f"\nWARNING: {len(other)} row(s) with unrecognised decision — treating as reject:")
        for r in other[:10]:
            print(f"  {r['artist']!r} / {r['title']!r} → {r.get('decision')!r}")

    if fixed:
        renames = [r for r in fixed if (r.get("fix_artist") or "").strip() or (r.get("fix_title") or "").strip()]
        value_fixes = [r for r in fixed if not (r.get("fix_artist") or "").strip() and not (r.get("fix_title") or "").strip()]
        if renames:
            print(f"\nRenames ({len(renames)}) — will clear album/duration for backfill retry:")
            for r in renames:
                new_a = (r.get("fix_artist") or "").strip() or r["artist"]
                new_t = (r.get("fix_title") or "").strip() or r["title"]
                fix_alb = (r.get("fix_album") or "").strip()
                fix_dur = (r.get("fix_duration_secs") or "").strip()
                print(f"  {r['artist']!r} / {r['title']!r}")
                print(f"    -> {new_a!r} / {new_t!r}")
                if fix_alb:
                    print(f"    album set to: {fix_alb!r}")
                if fix_dur:
                    print(f"    duration set to: {fix_dur}s")
        if value_fixes:
            print(f"\nValue fixes ({len(value_fixes)}):")
            for r in value_fixes:
                fix_alb = (r.get("fix_album") or "").strip()
                fix_dur = (r.get("fix_duration_secs") or "").strip()
                print(f"  {r['artist']!r} / {r['title']!r}")
                if fix_alb:
                    print(f"    album: {r.get('existing_album')!r} -> {fix_alb!r}")
                if fix_dur:
                    print(f"    duration: {r.get('existing_duration_secs')}s -> {fix_dur}s")
                if not fix_alb and not fix_dur:
                    print(f"    WARNING: all fix_* columns blank — nothing to write")

    if to_delete:
        print(f"\nTracks to delete ({len(to_delete)}):")
        for r in to_delete:
            print(f"  {r['artist']!r} / {r['title']!r}")

    renames_count = sum(1 for r in fixed if (r.get("fix_artist") or "").strip() or (r.get("fix_title") or "").strip())

    if not args.confirm:
        print(f"\nDry run — would apply {len(to_apply)} update(s) (incl. {renames_count} rename(s)), "
              f"delete {len(to_delete)} track(s), skip {len(rejected)} rejection(s).")
        if renames_count:
            print("Renamed tracks will need a backfill retry — run backfill_metadata.py after confirming.")
        print("Pass --confirm to apply.")
        return

    session = get_session()
    try:
        updates_applied, renames_applied = _apply_entries(to_apply, session)
        deleted = 0
        for r in to_delete:
            session.execute(
                sa_delete(Listen).where(
                    and_(Listen.artist == r["artist"], Listen.title == r["title"])
                )
            )
            deleted += 1
        session.commit()
    finally:
        session.close()

    print(f"\nApplied {updates_applied} metadata update(s), {renames_applied} rename(s), "
          f"deleted {deleted} track(s), skipped {len(rejected)} rejection(s).")
    if renames_applied:
        print("Run backfill_metadata.py to fill renamed tracks.")


def cmd_bulk_confirm(args: argparse.Namespace) -> None:
    updates = _load_updates(args.results, args.artist)
    # Bulk mode only applies skipped_update entries, not low-confidence skipped
    updates = [r for r in updates if r.get("action") == "skipped_update"]

    print(f"{'=== DRY RUN ===' if not args.confirm else '=== APPLYING ALL ==='}")
    print(f"\nTotal skipped_update entries: {len(updates)}")

    album_changes = [r for r in updates if r.get("existing_album") and r["existing_album"] != r.get("chosen_album")]
    duration_changes = [r for r in updates
                        if r.get("existing_duration_secs") and r.get("chosen_duration_secs")
                        and abs((r["existing_duration_secs"] or 0) - (r["chosen_duration_secs"] or 0)) > 5]
    album_fill = [r for r in updates if not r.get("existing_album") and r.get("chosen_album")]

    print(f"\nChange breakdown:")
    print(f"  Album corrections (existing → different): {len(album_changes)}")
    print(f"  Duration corrections (>5s difference):    {len(duration_changes)}")
    print(f"  Album fills (was null):                   {len(album_fill)}")
    print(f"  (Note: low-confidence 'skipped' entries excluded — use --generate-csv to review those)")

    if not args.confirm:
        print("\nDry run — pass --confirm to apply all, or use --generate-csv for per-row review.")
        return

    session = get_session()
    try:
        updates_applied, _ = _apply_entries(updates, session)
    finally:
        session.close()
    print(f"\nApplied {updates_applied} update(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", default=RESULTS_FILE, help="Path to backfill_results.json")
    parser.add_argument("--csv", default=CSV_FILE, help="CSV path for --generate-csv / --apply-csv")
    parser.add_argument("--artist", help="Filter to a specific artist")
    parser.add_argument("--generate-csv", action="store_true", help="Write skipped_updates_review.csv for manual review")
    parser.add_argument("--apply-csv", action="store_true", help="Apply decisions from the review CSV")
    parser.add_argument("--confirm", action="store_true", help="Apply changes (used with --apply-csv or bulk mode)")

    args = parser.parse_args()

    if args.generate_csv:
        cmd_generate_csv(args)
    elif args.apply_csv:
        cmd_apply_csv(args)
    else:
        cmd_bulk_confirm(args)


if __name__ == "__main__":
    main()
