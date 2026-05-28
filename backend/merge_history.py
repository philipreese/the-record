#!/usr/bin/env python3
"""
Merge YouTube Music watch history with Last.fm scrobbles.
Fetches all history from Last.fm, parses watch-history.json,
deduplicates them, and writes the consolidated history to merged_history.json.
"""

import os
import json
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")

# ── Parsing YouTube Music Takeout ──────────────────────────────────────────────

def strip_watched(title):
    """Remove 'Watched ' prefix from title."""
    if title.startswith("Watched "):
        return title[8:]
    return title

def parse_ytm_entry(entry):
    """
    Extract artist and title from a YouTube Music entry if it is a topic channel.
    Matches the logic of scrobble_adaptive.py.
    """
    if entry.get("header") != "YouTube Music":
        return None, None

    raw_title = strip_watched(entry.get("title", ""))
    subtitles = entry.get("subtitles", [])
    subtitle_name = subtitles[0]["name"] if subtitles else None

    if raw_title.startswith("http") or not subtitle_name:
        return None, None

    # Only import topic_channel entries
    if subtitle_name.endswith(" - Topic"):
        artist = subtitle_name[:-8]  # strip " - Topic"
        return artist, raw_title

    return None, None

def parse_ytm_timestamp(time_str):
    """Parse ISO 8601 timestamp with millisecond rounding to Unix epoch."""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return round(dt.timestamp())  # round to nearest second
    except Exception:
        return None

# ── Fetching Last.fm history ───────────────────────────────────────────────────

def fetch_lastfm_history(api_key, username):
    if not api_key or not username:
        print("Warning: Last.fm credentials missing from environment. Skipping Last.fm fetch.")
        return []

    print(f"Fetching all scrobbles for user '{username}' from Last.fm...")
    scrobbles = []
    page = 1

    while True:
        params = {
            "method": "user.getrecenttracks",
            "user": username,
            "api_key": api_key,
            "limit": 200,
            "page": page,
            "format": "json"
        }
        url = "https://ws.audioscrobbler.com/2.0/?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "the-record-consolidator/1.0"})
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"\nError fetching page {page}: {e}")
            break

        recent_tracks = data.get("recenttracks", {})
        tracks = recent_tracks.get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]
        if not tracks:
            break

        for t in tracks:
            # Skip currently playing track (which lacks a timestamped date field)
            if "@attr" in t and t["@attr"].get("nowplaying") == "true":
                continue

            uts = t.get("date", {}).get("uts")
            if uts:
                scrobbles.append({
                    "artist": t["artist"]["#text"],
                    "title": t["name"],
                    "unix_ts": int(uts),
                    "date_text": t["date"].get("#text", "")
                })

        attr = recent_tracks.get("@attr", {})
        total_pages = int(attr.get("totalPages", 1))
        print(f"  Page {page}/{total_pages} fetched. Collected {len(scrobbles)} scrobbles.", end="\r")

        if page >= total_pages:
            break
        page += 1
        time.sleep(0.2)

    print(f"\nSuccessfully fetched {len(scrobbles)} scrobbles from Last.fm.")
    return scrobbles

# ── Merging and Deduplication ─────────────────────────────────────────────────

def normalize(text):
    """Normalize string for robust comparison (lowercase, strip special chars)."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def merge_histories(ytm_list, lfm_list):
    """
    Merges YouTube Music and Last.fm histories.
    Keeps all YouTube Music history. Matches Last.fm scrobbles to YTM.
    Unmatched Last.fm scrobbles (like from 2010) are added as separate entries.
    """
    print(f"Merging {len(ytm_list):,} YouTube Music plays with {len(lfm_list):,} Last.fm scrobbles...")

    # Group YTM entries by rounded timestamp to make matching O(N + M) instead of O(N * M)
    ytm_by_time = {}
    for entry in ytm_list:
        ts = entry["unix_ts"]
        ytm_by_time.setdefault(ts, []).append(entry)

    matched_lfm_count = 0
    unmatched_lfm_entries = []

    for lfm in lfm_list:
        lfm_ts = lfm["unix_ts"]
        lfm_art = normalize(lfm["artist"])
        lfm_title = normalize(lfm["title"])

        # Look in a window of +/- 2 seconds
        matched = False
        for offset in [0, -1, 1, -2, 2]:
            target_ts = lfm_ts + offset
            if target_ts in ytm_by_time:
                for ytm in ytm_by_time[target_ts]:
                    ytm_art = normalize(ytm["artist"])
                    ytm_title = normalize(ytm["title"])

                    # If artist and title match (either identical or substrings)
                    artist_ok = (ytm_art == lfm_art) or (ytm_art in lfm_art) or (lfm_art in ytm_art)
                    title_ok = (ytm_title == lfm_title) or (ytm_title in lfm_title) or (lfm_title in ytm_title)

                    if artist_ok and title_ok:
                        matched = True
                        break
            if matched:
                break

        if matched:
            matched_lfm_count += 1
        else:
            unmatched_lfm_entries.append({
                "artist": lfm["artist"],
                "title": lfm["title"],
                "unix_ts": lfm["unix_ts"],
                "source": "last_fm"
            })

    print(f"  Matched {matched_lfm_count:,} Last.fm scrobbles to YouTube Music history.")
    print(f"  Found {len(unmatched_lfm_entries):,} unique Last.fm scrobbles (e.g. 2010 era, other platforms).")

    # Combine YTM entries with unmatched LFM entries
    merged_list = []
    for ytm in ytm_list:
        merged_list.append({
            "artist": ytm["artist"],
            "title": ytm["title"],
            "unix_ts": ytm["unix_ts"],
            "source": "youtube_music"
        })

    merged_list.extend(unmatched_lfm_entries)

    # Sort chronologically
    merged_list.sort(key=lambda e: e["unix_ts"])
    return merged_list

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ytm_path = "watch-history.json"
    if len(sys.argv) > 1:
        ytm_path = sys.argv[1]

    if not os.path.exists(ytm_path):
        print(f"Error: YouTube watch history file not found at '{ytm_path}'")
        print("Please place watch-history.json in the repository root.")
        sys.exit(1)

    print(f"Loading {ytm_path}...")
    try:
        with open(ytm_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading watch history file: {e}")
        sys.exit(1)

    print(f"Parsing YouTube Music Takeout data...")
    ytm_parsed = []
    for entry in data:
        artist, title = parse_ytm_entry(entry)
        if artist and title:
            ts = parse_ytm_timestamp(entry.get("time", ""))
            if ts:
                ytm_parsed.append({
                    "artist": artist,
                    "title": title,
                    "unix_ts": ts
                })

    print(f"Parsed {len(ytm_parsed):,} clean YouTube Music topic channel entries.")

    # Fetch Last.fm
    lfm_scrobbles = []
    if LASTFM_API_KEY and LASTFM_USERNAME:
        lfm_scrobbles = fetch_lastfm_history(LASTFM_API_KEY, LASTFM_USERNAME)
    else:
        print("\nLast.fm integration skipped: LASTFM_API_KEY or LASTFM_USERNAME not set.")
        print("Check your .env file. Merging will proceed with YouTube Music only.")

    # Merge
    merged = merge_histories(ytm_parsed, lfm_scrobbles)

    # Output results
    output_path = os.path.join("backend", "merged_history.json")
    print(f"Saving merged history to {output_path}...")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        print(f"Success! Saved {len(merged):,} total scrobbles.")
    except Exception as e:
        print(f"Error saving merged history: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
