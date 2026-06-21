"""
Generate failure_review.csv from backfill_failures.json for manual triage.

One row per failing track. Sort by artist in your editor to bulk-edit.
Edit the 'decision' column:
  keep        — leave in DB as-is (no MB metadata will be added)
  delete      — remove all listens for this specific track from DB
  fix         — correct the artist/title; fill fix_artist and/or fix_title columns

Leave fix_artist/fix_title blank if they don't need changing.
After applying fixes, backfill will be re-run on corrected entries automatically.

Run this after each backfill_metadata.py run (especially after --reverify).

Usage:
  python generate_review_csv.py
  python generate_review_csv.py --failures path/to/backfill_failures.json
"""

import csv
import json
import re
import os
import sys
import argparse
import collections

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8")

FAILURES_FILE = os.path.join(SCRIPT_DIR, "backfill_failures.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "failure_review.csv")

KNOWN_JUNK_ARTISTS = {
    "Goobsie", "Alex Melton", "432Won", "Channel 432 (hz)",
    "PowerThoughts Meditation Club", "Solfeggio Frequencies",
    "Theta Realms - Brainwave Sound Journeys", "AcrobaticArts",
    "Adrian von Ziegler", "Ambient Worlds", "Danheim",
    "Fantasy & World Music by the Fiechters", "Jonna Jinton",
    "Peter Gundry | Composer", "Yellow Brick Cinema - Relaxing Music",
    "Thriller Records", "Release",
}

JUNK_TITLE_RE = re.compile(
    r"mashup|mash-up|432\s*hz|binaural|solfeggio|relaxing|ambient|"
    r"cardio|workout|meditation|healing freq",
    re.IGNORECASE,
)


def suggest_decision(artist: str, title: str) -> str:
    if artist in KNOWN_JUNK_ARTISTS:
        return "delete"
    if re.search(r"VEVO$", artist, re.IGNORECASE):
        return "delete"
    if JUNK_TITLE_RE.search(title):
        return "delete"
    return "keep"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--failures", default=FAILURES_FILE, help="Path to backfill_failures.json")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output CSV path")
    args = parser.parse_args()

    with open(args.failures, encoding="utf-8") as f:
        failures = json.load(f)

    rows = []
    for e in failures:
        artist: str = e["artist"]
        title: str = e["title"]
        decision = suggest_decision(artist, title)
        rows.append({
            "artist": artist,
            "title": title,
            "decision": decision,
            "fix_artist": "",
            "fix_title": "",
            "notes": "",
        })

    # Sort: deletes first (so they're easy to bulk-confirm), then keep — alpha within each
    order = {"delete": 0, "keep": 1}
    rows.sort(key=lambda r: (order.get(r["decision"], 2), r["artist"].lower(), r["title"].lower()))

    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["artist", "title", "decision", "fix_artist", "fix_title", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    counts = collections.Counter(r["decision"] for r in rows)
    print(f"Wrote {len(rows)} tracks to {args.output}")
    print(f"  Pre-marked delete: {counts['delete']}")
    print(f"  Defaulted keep:    {counts['keep']}")
    print()
    print("Columns:")
    print("  decision  — keep / delete / fix")
    print("  fix_artist — new artist name (only needed when decision=fix)")
    print("  fix_title  — new title (only needed when decision=fix and title is wrong)")
    print()
    print("After editing, run: python apply_review_decisions.py --confirm")


if __name__ == "__main__":
    main()
