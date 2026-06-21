"""
One-time cleanup of garbage and fixable entries from backfill_failures.json.

Phase 1 — DELETE: removes listens that are YouTube junk (mashups, covers,
          ambient channels, 432hz reposts, fan recordings, unattributable
          label/channel content).

Phase 2 — FIX: for VEVO channels and label channels whose title embeds the
          real artist ("A Day To Remember - All I Want"), extracts the correct
          artist/title and updates the DB rows so backfill can retry them.

Writes fix_output.json with the corrected (artist, title) pairs so you can
re-run backfill_metadata.py --artists-file fix_output.json on just those tracks.

Usage:
  python fix_failure_entries.py           # dry run
  python fix_failure_entries.py --confirm # apply changes
"""

import sys
import os
import json
import argparse
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from app.db import get_session, Listen
from app.utils import clean_artist, clean_title
from app.repository import deduplicate_listens
from sqlalchemy import select, delete as sa_delete, and_, update

FAILURES_FILE = os.path.join(SCRIPT_DIR, "backfill_failures.json")
FIX_OUTPUT_FILE = os.path.join(SCRIPT_DIR, "fix_output.json")

# ── Artists/titles to delete entirely ─────────────────────────────────────────

# Channel names where ALL their content is garbage
JUNK_ARTISTS = {
    # Mashup channels
    "Goobsie",
    # Cover/YouTube-only channels
    "Alex Melton",
    # 432hz repost channels
    "432Won",
    "Channel 432 (hz)",
    "PowerThoughts Meditation Club",
    "Solfeggio Frequencies",
    "Theta Realms - Brainwave Sound Journeys",
    # Ambient YouTube channels (not real music releases)
    "Adrian von Ziegler",
    "Ambient Worlds",
    "Danheim",
    "Fantasy & World Music by the Fiechters",
    "Jonna Jinton",
    "Peter Gundry | Composer",
    "Yellow Brick Cinema - Relaxing Music",
    # Non-music
    "AcrobaticArts",
    # Label channels posting tracks with no artist attribution in title
    "Thriller Records",
    "Release",
}

# Specific (artist, title) pairs that are fan recordings or unattributable
JUNK_PAIRS = {
    ("Adam Speirs", "Sleep Token - Fall for me, from the room below - live @ Lafayette, london UK, 29th April 2022"),
    ("HurricaneFstvl", "DIE ANTWOORD - I Fink U Freeky (Live At Hurricane Festival 2015)"),
    ("Smithsonian Folkways", "Ceri Rhys Matthews Performs with Ceri Ashton & Members of Sild [Live at Folklife Festival 2009]"),
    ("AcrobaticArts", "Cardio Time!"),
}

# ── VEVO channel detection ─────────────────────────────────────────────────────

def is_vevo(artist: str) -> bool:
    return bool(re.search(r"VEVO$", artist, re.IGNORECASE))

# ── Label channel detection (channel posts "Artist - Title" videos) ────────────

# These are label/channel artists where the title carries "Real Artist - Song"
LABEL_ARTISTS = {
    "4AD",
    "Atlantic Records",
    "Century Media Records",
    "Epitaph Records",
    "Equal Vision Records",
    "F00L",
    "FacedownRecords",
    "Fearless Records",
    "Hopeless Records",
    "InVogue Records",
    "MQ",
    "Mutant League Records",
    "Napalm Records",
    "Nuclear Blast Records",
    "Polyvinyl Records",
    "Red Bull Records",
    "Run For Cover Records",
    "SharpTone Records",
    "Solid State Records",
    "Trillium Records",
    "Triple Crown Records",
    "UNFD",
    "VisibleNoiseRecords",
    "Warner Records Vault",
    "adventure cat records.",
    "riserecords",
}


def extract_artist_title_from_prefix(title: str) -> tuple[str, str] | None:
    """Split 'Artist - Song Title' → (artist, title). Handles hyphen and en/em-dashes."""
    for sep in [" - ", " – ", " — "]:
        if sep in title:
            artist_part, _, title_part = title.partition(sep)
            artist_part = artist_part.strip()
            title_part = title_part.strip()
            if artist_part and title_part:
                return clean_artist(artist_part), clean_title(title_part)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="Apply changes (default is dry run)")
    args = parser.parse_args()

    with open(FAILURES_FILE, encoding="utf-8") as f:
        failures = json.load(f)

    # Build action lists
    to_delete_artist: list[str] = []     # all listens with this artist
    to_delete_pair: list[tuple[str, str]] = []  # specific (artist, title)
    to_fix: list[tuple[str, str, str, str]] = []  # (old_artist, old_title, new_artist, new_title)
    skipped: list[dict] = []

    for e in failures:
        artist: str = e["artist"]
        title: str = e["title"]

        # Phase 1a: whole-artist junk
        if artist in JUNK_ARTISTS:
            to_delete_artist.append(artist)
            continue

        # Phase 1b: specific pair junk
        if (artist, title) in JUNK_PAIRS:
            to_delete_pair.append((artist, title))
            continue

        # Phase 2a: VEVO channel — extract real artist from title
        if is_vevo(artist):
            extracted = extract_artist_title_from_prefix(title)
            if extracted:
                new_artist, new_title = extracted
                to_fix.append((artist, title, new_artist, new_title))
            else:
                to_delete_pair.append((artist, title))
            continue

        # Phase 2b: known label channel with "Artist - Title" in track name
        if artist in LABEL_ARTISTS:
            extracted = extract_artist_title_from_prefix(title)
            if extracted:
                new_artist, new_title = extracted
                to_fix.append((artist, title, new_artist, new_title))
            else:
                to_delete_pair.append((artist, title))
            continue

        # Phase 2c: ✝✝✝ (Crosses) — Unicode symbols likely break the MB Lucene query;
        # query as "Crosses" instead (that's the common name MB indexes them under)
        if artist == "✝✝✝ (Crosses)":
            to_fix.append((artist, title, "Crosses", title))
            continue

        skipped.append(e)

    # Deduplicate to_delete_artist list
    to_delete_artist = list(set(to_delete_artist))

    print(f"=== DRY RUN ===" if not args.confirm else "=== APPLYING CHANGES ===")
    print(f"\nPhase 1 — DELETE")
    print(f"  Artists to purge entirely: {len(to_delete_artist)}")
    for a in sorted(to_delete_artist):
        print(f"    {a!r}")
    print(f"  Specific pairs to delete: {len(to_delete_pair)}")
    for a, t in to_delete_pair:
        print(f"    {a!r} / {t!r}")

    print(f"\nPhase 2 — FIX ({len(to_fix)} entries)")
    for old_a, old_t, new_a, new_t in to_fix:
        print(f"  {old_a!r} / {old_t!r}")
        print(f"    -> {new_a!r} / {new_t!r}")

    print(f"\nSkipped (no action, leaving in DB): {len(skipped)}")

    if not args.confirm:
        print("\nDry run complete — pass --confirm to apply.")
        return

    session = get_session()
    deleted_rows = 0
    fixed_rows = 0

    try:
        # Delete by artist
        for artist in to_delete_artist:
            result = session.execute(
                sa_delete(Listen).where(Listen.artist == artist)
            )
            deleted_rows += result.rowcount

        # Delete specific pairs
        for artist, title in to_delete_pair:
            result = session.execute(
                sa_delete(Listen).where(
                    and_(Listen.artist == artist, Listen.title == title)
                )
            )
            deleted_rows += result.rowcount

        session.commit()
        print(f"\nDeleted {deleted_rows} listen row(s).")

        # Fix entries
        for old_artist, old_title, new_artist, new_title in to_fix:
            result = session.execute(
                update(Listen)
                .where(and_(Listen.artist == old_artist, Listen.title == old_title))
                .values(artist=new_artist, title=new_title)
            )
            fixed_rows += result.rowcount

        session.commit()
        print(f"Fixed {fixed_rows} listen row(s).")

        # Deduplicate in case any fixes caused collisions
        dupes = deduplicate_listens()
        print(f"Deduplicated {dupes} duplicate row(s).")

    finally:
        session.close()

    # Write fix_output.json for targeted backfill retry
    fix_targets = [{"artist": new_a, "title": new_t} for _, _, new_a, new_t in to_fix]
    # Also add ✝✝✝ (Crosses) with alternate query name
    crosses_entries = [e for e in failures if "✝✝✝" in e.get("artist", "")]
    for e in crosses_entries:
        fix_targets.append({"artist": "Crosses", "title": e["title"], "_original_artist": e["artist"]})

    with open(FIX_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(fix_targets, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(fix_targets)} entries to {FIX_OUTPUT_FILE} for backfill retry.")
    print("Next: update backfill_metadata.py to accept --targets-file and re-run on just these.")


if __name__ == "__main__":
    main()
