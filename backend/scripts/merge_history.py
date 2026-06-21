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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

sys.path.insert(0, BACKEND_DIR)
from app.utils import clean_artist, clean_title, strip_artist_prefix  # noqa: E402

load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")

# ── Parsing YouTube Music Takeout ──────────────────────────────────────────────

def strip_watched(title):
    """Remove 'Watched ' prefix from title."""
    if title.startswith("Watched "):
        return title[8:]
    return title

def parse_yt_entry(entry):
    """
    Extract artist and title from a YouTube Music entry.
    Only allows entries where header == "YouTube Music".
    """
    header = entry.get("header", "")
    if header != "YouTube Music":
        return None, None

    # Extract title (strip "Watched " prefix)
    raw_title = entry.get("title", "")
    if raw_title.startswith("Watched "):
        raw_title = raw_title[8:]
        
    if not raw_title or raw_title.startswith("http"):
        return None, None

    # Extract artist from subtitles
    subtitles = entry.get("subtitles", [])
    if not subtitles:
        return None, None
        
    subtitle_name = subtitles[0].get("name", "")
    if not subtitle_name:
        return None, None

    # If it ends with " - Topic", strip it.
    if subtitle_name.endswith(" - Topic"):
        artist = subtitle_name[:-8]
    else:
        artist = subtitle_name

    return clean_artist(artist), clean_title(strip_artist_prefix(raw_title, artist))

def filter_rapid_skips(parsed_list):
    """
    Remove tracks that are followed by another track in less than 30 seconds.
    This filters out fast skips and batch-loaded library/playlist syncs.
    """
    if not parsed_list:
        return []
    # Sort chronologically to check consecutive gaps
    parsed_list.sort(key=lambda e: e["unix_ts"])
    filtered = []
    for i in range(len(parsed_list)):
        if i < len(parsed_list) - 1:
            time_diff = parsed_list[i+1]["unix_ts"] - parsed_list[i]["unix_ts"]
            if time_diff < 30:
                continue
        filtered.append(parsed_list[i])
    return filtered


def parse_ytm_timestamp(time_str):
    """Parse ISO 8601 timestamp with millisecond rounding to Unix epoch."""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return round(dt.timestamp())  # round to nearest second
    except Exception:
        return None

def deduplicate_myactivity(watch_list, myact_list, window=43200):
    """
    Deduplicate MyActivity plays against base watch history using a greedy one-to-one matching algorithm.
    Returns: (added_list, skipped_count)
    """
    # Group watch history timestamps by track key
    watch_tracks = {}
    for entry in watch_list:
        key = (normalize(entry["artist"]), normalize(entry["title"]))
        watch_tracks.setdefault(key, []).append(entry["unix_ts"])
        
    # Group MyActivity entries by track key
    myact_by_track = {}
    for entry in myact_list:
        key = (normalize(entry["artist"]), normalize(entry["title"]))
        myact_by_track.setdefault(key, []).append(entry)
        
    added_list = []
    skipped_dup_count = 0
    
    for key, m_entries in myact_by_track.items():
        w_timestamps = watch_tracks.get(key, [])
        
        # Match each w_ts to the closest unmatched m_entry within the window
        matched_m_indices = set()
        
        w_sorted = sorted(w_timestamps)
        m_sorted_entries = sorted(m_entries, key=lambda e: e["unix_ts"])
        
        for w_ts in w_sorted:
            closest_m_idx = None
            min_diff = None
            
            for i, entry in enumerate(m_sorted_entries):
                if i in matched_m_indices:
                    continue
                diff = abs(w_ts - entry["unix_ts"])
                if diff <= window:
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_m_idx = i
            
            if closest_m_idx is not None:
                matched_m_indices.add(closest_m_idx)
        
        # Any entry that was not matched is a truly new recovered play
        for i, entry in enumerate(m_sorted_entries):
            if i in matched_m_indices:
                skipped_dup_count += 1
            else:
                added_list.append(entry)
                
    return added_list, skipped_dup_count

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
    # 1. Load watch-history.json (base history)
    watch_path = os.path.join(PROJECT_ROOT, "watch-history.json")
    watch_parsed = []
    if os.path.exists(watch_path):
        print(f"Loading {watch_path}...")
        try:
            with open(watch_path, "r", encoding="utf-8") as f:
                watch_data = json.load(f)
            for entry in watch_data:
                artist, title = parse_yt_entry(entry)
                if artist and title:
                    ts = parse_ytm_timestamp(entry.get("time", ""))
                    if ts:
                        watch_parsed.append({
                            "artist": artist,
                            "title": title,
                            "unix_ts": ts
                        })
            print(f"Parsed {len(watch_parsed):,} entries from watch-history.json.")
            watch_parsed = filter_rapid_skips(watch_parsed)
            print(f"Filtered to {len(watch_parsed):,} plays (removed skips/bursts) in watch-history.json.")
        except Exception as e:
            print(f"Warning: Error reading/parsing watch-history.json: {e}")

    # 2. Load MyActivity.json (for recovering missing/older plays)
    myact_path = os.path.join(PROJECT_ROOT, "MyActivity.json")
    myact_parsed = []
    if os.path.exists(myact_path):
        print(f"Loading {myact_path}...")
        try:
            with open(myact_path, "r", encoding="utf-8") as f:
                myact_data = json.load(f)
            
            # Filter to >= 2020-01-01 UTC (timestamp >= 1577836800)
            cutoff_ts = 1577836800
            for entry in myact_data:
                artist, title = parse_yt_entry(entry)
                if artist and title:
                    ts = parse_ytm_timestamp(entry.get("time", ""))
                    if ts and ts >= cutoff_ts:
                        myact_parsed.append({
                            "artist": artist,
                            "title": title,
                            "unix_ts": ts
                        })
            print(f"Parsed {len(myact_parsed):,} entries (>= 2020) from MyActivity.json.")
            myact_parsed = filter_rapid_skips(myact_parsed)
            print(f"Filtered to {len(myact_parsed):,} plays (removed skips/bursts) in MyActivity.json.")
        except Exception as e:
            print(f"Warning: Error reading/parsing MyActivity.json: {e}")

    if not watch_parsed and not myact_parsed:
        print("Error: No history data found. Please place watch-history.json or MyActivity.json in the repository root.")
        sys.exit(1)

    # 3. Combine both histories, skipping 12-hour duplicates from MyActivity.json using greedy one-to-one matching
    combined_ytm = list(watch_parsed)
    
    if myact_parsed:
        print("Deduplicating MyActivity.json against base history (greedy 12-hour window)...")
        recovered_added, skipped_dup_count = deduplicate_myactivity(combined_ytm, myact_parsed, window=12*3600)
        combined_ytm.extend(recovered_added)
        print(f"  Added {len(recovered_added):,} unique recovered plays from MyActivity.json.")
        print(f"  Skipped {skipped_dup_count:,} shifted duplicate plays.")

    combined_ytm.sort(key=lambda e: e["unix_ts"])
    print(f"Total consolidated YouTube Music plays: {len(combined_ytm):,}")

    # Fetch Last.fm
    lfm_scrobbles = []
    if LASTFM_API_KEY and LASTFM_USERNAME:
        lfm_scrobbles = fetch_lastfm_history(LASTFM_API_KEY, LASTFM_USERNAME)
    else:
        print("\nLast.fm integration skipped: LASTFM_API_KEY or LASTFM_USERNAME not set.")
        print("Check your .env file. Merging will proceed with YouTube Music only.")

    # Merge combined YTM with Last.fm
    merged = merge_histories(combined_ytm, lfm_scrobbles)

    # Output results
    output_path = os.path.join(PROJECT_ROOT, "backend", "merged_history.json")
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
