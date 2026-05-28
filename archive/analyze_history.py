#!/usr/bin/env python3
"""
YouTube Music Watch History Analyzer
Parses watch-history.json and reports what it finds before any scrobbling.
Usage: python analyze_history.py watch-history.json
"""

import json
import sys
import re
from collections import Counter
from datetime import datetime, timezone

def strip_watched(title):
    """Remove 'Watched ' prefix from title."""
    if title.startswith("Watched "):
        return title[8:]
    return title

def parse_artist_title(entry):
    """
    Try to extract artist and title from a YouTube Music entry.
    Returns (artist, title, method) where method describes how we got there.
    """
    raw_title = strip_watched(entry.get("title", ""))
    subtitles = entry.get("subtitles", [])
    subtitle_name = subtitles[0]["name"] if subtitles else None

    # Method 1: subtitle ends with " - Topic" → clean artist name
    if subtitle_name and subtitle_name.endswith(" - Topic"):
        artist = subtitle_name[:-8]  # strip " - Topic"
        return artist, raw_title, "topic_channel"

    # Method 2: VEVO or similar — title contains "ARTIST - Title" pattern
    if subtitle_name and " - " in raw_title:
        parts = raw_title.split(" - ", 1)
        return parts[0].strip(), parts[1].strip(), "title_split"

    # Method 3: subtitle exists but neither above matched — use subtitle as artist
    if subtitle_name:
        return subtitle_name, raw_title, "subtitle_fallback"

    # Method 4: no subtitle at all
    return None, raw_title, "no_artist"

def parse_timestamp(time_str):
    """Parse ISO 8601 timestamp to Unix epoch."""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_history.py watch-history.json")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Loading {path}...")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Total entries in file: {len(data):,}")

    # Split by header
    yt_music = [e for e in data if e.get("header") == "YouTube Music"]
    yt_regular = [e for e in data if e.get("header") == "YouTube"]
    other = [e for e in data if e.get("header") not in ("YouTube Music", "YouTube")]

    print(f"\n--- Entry breakdown ---")
    print(f"YouTube Music entries : {len(yt_music):,}")
    print(f"YouTube entries       : {len(yt_regular):,}")
    print(f"Other headers         : {len(other):,}")
    if other:
        other_headers = Counter(e.get("header") for e in other)
        for h, c in other_headers.most_common():
            print(f"  '{h}': {c:,}")

    # Analyze YouTube Music entries
    print(f"\n--- YouTube Music analysis ---")
    methods = Counter()
    no_subtitle = []
    samples = {"topic_channel": [], "title_split": [], "subtitle_fallback": [], "no_artist": []}
    timestamps = []
    multi_subtitle = []

    for entry in yt_music:
        subtitles = entry.get("subtitles", [])
        if len(subtitles) > 1:
            multi_subtitle.append(entry)

        artist, title, method = parse_artist_title(entry)
        methods[method] += 1

        ts = parse_timestamp(entry.get("time", ""))
        if ts:
            timestamps.append(ts)

        if len(samples[method]) < 3:
            samples[method].append((artist, title, entry.get("subtitles", [{}])[0].get("name", "N/A") if entry.get("subtitles") else "N/A"))

    print(f"\nParsing method breakdown:")
    for method, count in methods.most_common():
        pct = 100 * count / len(yt_music) if yt_music else 0
        print(f"  {method:<22} {count:>7,}  ({pct:.1f}%)")

    print(f"\nEntries with multiple subtitles: {len(multi_subtitle):,}")

    if timestamps:
        earliest = datetime.fromtimestamp(min(timestamps), tz=timezone.utc)
        latest = datetime.fromtimestamp(max(timestamps), tz=timezone.utc)
        print(f"\nDate range:")
        print(f"  Earliest : {earliest.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  Latest   : {latest.strftime('%Y-%m-%d %H:%M UTC')}")

    print(f"\n--- Sample parsed entries by method ---")
    for method, sample_list in samples.items():
        if sample_list:
            print(f"\n[{method}]")
            for artist, title, raw_subtitle in sample_list:
                print(f"  Artist : {artist}")
                print(f"  Title  : {title}")
                print(f"  Raw sub: {raw_subtitle}")
                print()

    print(f"\n--- Summary ---")
    print(f"Ready to scrobble  : {methods['topic_channel'] + methods['title_split'] + methods['subtitle_fallback']:,}")
    print(f"Missing artist     : {methods['no_artist']:,}")
    print(f"\nRun this script first, review the samples above,")
    print(f"then run the scrobble script when you're happy with the parsing.")

if __name__ == "__main__":
    main()
