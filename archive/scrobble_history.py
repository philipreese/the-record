#!/usr/bin/env python3
"""
YouTube Music History → Last.fm Scrobbler
Scrobbles clean entries (topic_channel method only) and outputs uncertain
entries to a CSV for manual review.

Usage:
    python scrobble_history.py watch-history.json

Requirements:
    pip install pylast

You'll be prompted for your Last.fm API key, API secret, username, and password.
"""

import json
import sys
import csv
import time
import re
from datetime import datetime, timezone
from collections import Counter

try:
    import pylast
except ImportError:
    print("Missing dependency. Run: pip install pylast")
    sys.exit(1)

# ── Parsing helpers ────────────────────────────────────────────────────────────

def strip_watched(title):
    if title.startswith("Watched "):
        return title[8:]
    return title

def parse_entry(entry):
    """
    Returns (artist, title, method) for a YouTube Music entry.
    method is one of: topic_channel, title_split, subtitle_fallback, no_artist
    """
    raw_title = strip_watched(entry.get("title", ""))
    subtitles = entry.get("subtitles", [])
    subtitle_name = subtitles[0]["name"] if subtitles else None

    # Raw URL in title field — data capture failure
    if raw_title.startswith("http"):
        return None, raw_title, "no_artist"

    # No subtitle at all
    if not subtitle_name:
        return None, raw_title, "no_artist"

    # Clean: official topic channel
    if subtitle_name.endswith(" - Topic"):
        artist = subtitle_name[:-8]
        return artist, raw_title, "topic_channel"

    # Label/VEVO upload with "Artist - Title" in the title
    if " - " in raw_title:
        parts = raw_title.split(" - ", 1)
        return parts[0].strip(), parts[1].strip(), "title_split"

    # Subtitle exists but doesn't match known patterns
    return subtitle_name, raw_title, "subtitle_fallback"

def parse_timestamp(time_str):
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return None

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python scrobble_history.py watch-history.json")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Loading {path}...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Filter to YouTube Music only
    yt_music = [e for e in data if e.get("header") == "YouTube Music"]
    print(f"YouTube Music entries: {len(yt_music):,}")

    # Parse all entries
    clean = []       # topic_channel → scrobble
    review = []      # everything else → CSV

    for entry in yt_music:
        artist, title, method = parse_entry(entry)
        ts = parse_timestamp(entry.get("time", ""))
        subtitles = entry.get("subtitles", [])
        raw_subtitle = subtitles[0]["name"] if subtitles else ""
        url = entry.get("titleUrl", "").replace("\\u003d", "=")

        row = {
            "method": method,
            "timestamp": entry.get("time", ""),
            "unix_ts": ts,
            "parsed_artist": artist or "",
            "parsed_title": title or "",
            "raw_title": entry.get("title", ""),
            "raw_subtitle": raw_subtitle,
            "url": url,
        }

        if method == "topic_channel":
            clean.append(row)
        else:
            review.append(row)

    print(f"\nClean entries (will scrobble) : {len(clean):,}")
    print(f"Review entries (CSV)          : {len(review):,}")

    # Write review CSV
    review_path = "manual_review.csv"
    with open(review_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "method", "timestamp", "unix_ts",
            "parsed_artist", "parsed_title",
            "raw_title", "raw_subtitle", "url"
        ])
        writer.writeheader()
        writer.writerows(review)
    print(f"\nReview CSV written: {review_path}")
    print("Edit 'parsed_artist' and 'parsed_title' columns, then run the")
    print("manual scrobble script to submit those entries separately.\n")

    # ── Last.fm credentials ────────────────────────────────────────────────────
    print("=" * 50)
    print("Last.fm credentials")
    print("=" * 50)
    api_key    = input("API key    : ").strip()
    api_secret = input("API secret : ").strip()
    username   = input("Username   : ").strip()
    password   = input("Password   : ").strip()

    network = pylast.LastFMNetwork(
        api_key=api_key,
        api_secret=api_secret,
        username=username,
        password_hash=pylast.md5(password),
    )
    print("\nConnected to Last.fm ✓")

    # ── Scrobble in batches of 50 ──────────────────────────────────────────────
    # Last.fm requires timestamps ≤ now and rejects future timestamps.
    # Sort oldest-first so history builds naturally.
    clean_valid = [r for r in clean if r["unix_ts"] is not None]
    clean_valid.sort(key=lambda r: r["unix_ts"])

    now_ts = int(time.time())
    future = [r for r in clean_valid if r["unix_ts"] > now_ts]
    if future:
        print(f"\nSkipping {len(future):,} entries with future timestamps.")
        clean_valid = [r for r in clean_valid if r["unix_ts"] <= now_ts]

    total = len(clean_valid)
    print(f"\nScrobbling {total:,} entries in batches of 50...")
    print("This may take a while. Do not close the terminal.\n")

    BATCH_SIZE = 50
    submitted = 0
    errors = 0

    for i in range(0, total, BATCH_SIZE):
        batch = clean_valid[i:i + BATCH_SIZE]
        scrobbles = []
        for row in batch:
            scrobbles.append({
                "artist": row["parsed_artist"],
                "title":  row["parsed_title"],
                "timestamp": row["unix_ts"],
            })

        try:
            network.scrobble_many(scrobbles)
            submitted += len(batch)
        except pylast.WSError as e:
            print(f"  WSError on batch {i//BATCH_SIZE + 1}: {e}")
            errors += len(batch)
        except Exception as e:
            print(f"  Error on batch {i//BATCH_SIZE + 1}: {e}")
            errors += len(batch)

        # Progress every 10 batches (500 scrobbles)
        if (i // BATCH_SIZE + 1) % 10 == 0 or i + BATCH_SIZE >= total:
            pct = 100 * submitted / total if total else 0
            print(f"  {submitted:>6,} / {total:,} submitted ({pct:.1f}%)")

        # Polite rate limiting — Last.fm allows ~5 req/s, batches of 50 = fine
        time.sleep(0.2)

    print(f"\n{'='*50}")
    print(f"Done.")
    print(f"  Submitted : {submitted:,}")
    print(f"  Errors    : {errors:,}")
    print(f"  Review CSV: {review_path} ({len(review):,} entries)")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
