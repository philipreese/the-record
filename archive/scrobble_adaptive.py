#!/usr/bin/env python3
"""
YouTube Music History → Last.fm Adaptive Scrobbler
Uses pylast only for authentication, direct HTTP for all API calls.

- Seeds checkpoint from existing Last.fm scrobbles on first run
- Starts at 1s delay between batches, backs off if dropping detected
- Sessions of 500, batches of 50 (Last.fm max per call)
- Saves progress to checkpoint file — safe to interrupt and resume

Usage:
    python scrobble_adaptive.py watch-history.json

Requirements:
    pip install pylast
"""

import json
import sys
import time
import os
import pickle
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone

try:
    import pylast
except ImportError:
    print("Missing dependency. Run: pip install pylast")
    sys.exit(1)

CHECKPOINT_FILE = "scrobble_checkpoint.pkl"
SESSION_SIZE    = 500
BATCH_SIZE      = 50
INITIAL_DELAY   = 1.0
MAX_DELAY       = 30.0
BACKOFF_FACTOR  = 2.0
API_BASE        = "https://ws.audioscrobbler.com/2.0/"

# ── Auth ───────────────────────────────────────────────────────────────────────

def get_session_key(api_key, api_secret, username, password):
    """Use pylast to authenticate and extract the session key string."""
    network = pylast.LastFMNetwork(
        api_key=api_key,
        api_secret=api_secret,
        username=username,
        password_hash=pylast.md5(password),
    )
    # Trigger auth by making a simple authenticated call
    user = network.get_authenticated_user()
    # Extract session key from the network object
    return network.session_key

# ── API helpers ────────────────────────────────────────────────────────────────

def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def api_sig(params, secret):
    keys = sorted(k for k in params if k != "format")
    sig_str = "".join(k + str(params[k]) for k in keys) + secret
    return md5(sig_str)

def api_get(**params):
    params["format"] = "json"
    url = API_BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

def api_post(api_key, api_secret, session_key, **params):
    params["api_key"] = api_key
    params["sk"]      = session_key
    params["api_sig"] = api_sig(params, api_secret)
    params["format"]  = "json"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API_BASE, data=data, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_scrobble_count(api_key, username):
    result = api_get(method="user.getinfo", api_key=api_key, user=username)
    return int(result["user"]["playcount"])

# ── Parsing ────────────────────────────────────────────────────────────────────

def parse_entry(entry):
    raw_title = entry.get("title", "")
    if raw_title.startswith("Watched "):
        raw_title = raw_title[8:]
    subtitles = entry.get("subtitles", [])
    subtitle_name = subtitles[0]["name"] if subtitles else None
    if raw_title.startswith("http") or not subtitle_name:
        return None, None
    if subtitle_name.endswith(" - Topic"):
        return subtitle_name[:-8], raw_title
    return None, None

def parse_timestamp(time_str):
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return round(dt.timestamp())  # round to nearest second to match Last.fm storage
    except Exception:
        return None

# ── Checkpoint ─────────────────────────────────────────────────────────────────

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "rb") as f:
            return pickle.load(f)
    return None

def save_checkpoint(checkpoint):
    with open(CHECKPOINT_FILE, "wb") as f:
        pickle.dump(checkpoint, f)

# ── Seed ───────────────────────────────────────────────────────────────────────

def seed_from_lastfm(api_key, username):
    print("No checkpoint found — seeding from existing Last.fm history...")
    total = get_scrobble_count(api_key, username)
    print(f"  Total scrobbles on Last.fm: {total:,}")

    timestamps = set()
    page = 1

    while True:
        result = api_get(
            method="user.getrecenttracks",
            api_key=api_key,
            user=username,
            limit=200,
            page=page,
            extended=0,
        )
        tracks = result.get("recenttracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]
        if not tracks:
            break

        for t in tracks:
            date = t.get("date")
            if isinstance(date, dict) and date.get("uts"):
                timestamps.add(int(date["uts"]))

        attr = result.get("recenttracks", {}).get("@attr", {})
        total_pages = int(attr.get("totalPages", 1))
        print(f"  Page {page}/{total_pages} — {len(timestamps):,} timestamps collected...", end="\r")

        if page >= total_pages:
            break
        page += 1
        time.sleep(0.5)

    print(f"\n  Seeded {len(timestamps):,} existing timestamps into checkpoint.")
    return timestamps

# ── Scrobble batch ─────────────────────────────────────────────────────────────

def scrobble_batch(api_key, api_secret, session_key, batch):
    params = {"method": "track.scrobble"}
    for idx, entry in enumerate(batch):
        params[f"artist[{idx}]"]    = entry["artist"]
        params[f"track[{idx}]"]     = entry["title"]
        params[f"timestamp[{idx}]"] = str(entry["unix_ts"])
    return api_post(api_key, api_secret, session_key, **params)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python scrobble_adaptive.py watch-history.json")
        sys.exit(1)

    print(f"Loading {sys.argv[1]}...")
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = []
    for entry in data:
        if entry.get("header") != "YouTube Music":
            continue
        artist, title = parse_entry(entry)
        if not artist or not title:
            continue
        ts = parse_timestamp(entry.get("time", ""))
        if not ts:
            continue
        entries.append({"artist": artist, "title": title, "unix_ts": ts})

    entries.sort(key=lambda e: e["unix_ts"])
    now_ts = int(time.time())
    two_weeks_ago = now_ts - (14 * 24 * 60 * 60)
    entries = [e for e in entries if e["unix_ts"] <= now_ts]
    submittable = [e for e in entries if e["unix_ts"] >= two_weeks_ago]
    print(f"Parsed {len(entries):,} clean entries.")
    print(f"Within Last.fm 2-week window: {len(submittable):,}")
    entries = submittable

    print("\n" + "=" * 50)
    print("Last.fm credentials")
    print("=" * 50)
    api_key    = input("API key    : ").strip()
    api_secret = input("API secret : ").strip()
    username   = input("Username   : ").strip()
    password   = input("Password   : ").strip()

    print("Authenticating...")
    session_key = get_session_key(api_key, api_secret, username, password)
    print("Authenticated ✓\n")

    # Load or seed checkpoint
    checkpoint = load_checkpoint()
    if checkpoint is None:
        submitted_ts = seed_from_lastfm(api_key, username)
        checkpoint = {"submitted_timestamps": submitted_ts, "delay": INITIAL_DELAY}
        save_checkpoint(checkpoint)
    else:
        print(f"Checkpoint loaded: {len(checkpoint['submitted_timestamps']):,} already submitted.")

    delay        = checkpoint.get("delay", INITIAL_DELAY)
    submitted_ts = checkpoint["submitted_timestamps"]
    pending      = [e for e in entries if e["unix_ts"] not in submitted_ts]
    print(f"Pending entries: {len(pending):,}")

    if not pending:
        print("Nothing left to submit — all done!")
        return

    print(f"Starting with {delay}s delay. Sessions of {SESSION_SIZE}, batches of {BATCH_SIZE}.\n")

    total_landed  = 0
    total_dropped = 0
    i = 0

    while i < len(pending):
        session      = pending[i:i + SESSION_SIZE]
        count_before = get_scrobble_count(api_key, username)
        session_sent = 0

        for j in range(0, len(session), BATCH_SIZE):
            batch = session[j:j + BATCH_SIZE]
            try:
                scrobble_batch(api_key, api_secret, session_key, batch)
                session_sent += len(batch)
            except Exception as e:
                print(f"\n  Batch error: {e}")
            time.sleep(delay)

        time.sleep(5)
        count_after = get_scrobble_count(api_key, username)
        landed      = count_after - count_before
        dropped     = session_sent - landed
        total_landed  += landed
        total_dropped += max(dropped, 0)

        dt_oldest = datetime.fromtimestamp(session[0]["unix_ts"],  tz=timezone.utc).strftime("%Y-%m-%d")
        dt_newest = datetime.fromtimestamp(session[-1]["unix_ts"], tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"Session {i//SESSION_SIZE + 1}: sent {session_sent}, landed {landed}, "
              f"dropped {max(dropped,0)}  [{dt_oldest} → {dt_newest}]  delay={delay}s")

        if dropped > 0:
            delay = min(delay * BACKOFF_FACTOR, MAX_DELAY)
            print(f"  ⚠ Dropping detected — backing off to {delay}s")
        elif delay > INITIAL_DELAY:
            delay = max(delay / BACKOFF_FACTOR, INITIAL_DELAY)
            print(f"  ✓ No drops — recovering to {delay}s")

        # Only mark as submitted what actually landed
        for e in session[:landed]:
            submitted_ts.add(e["unix_ts"])
        checkpoint["submitted_timestamps"] = submitted_ts
        checkpoint["delay"]                = delay
        save_checkpoint(checkpoint)

        i += SESSION_SIZE
        if i < len(pending):
            pause = 30
            print(f"  Pausing {pause:.0f}s before next session...\n")
            time.sleep(pause)

    print(f"\n{'='*50}")
    print(f"Done.  Landed: {total_landed:,}  Dropped: {total_dropped:,}")
    print(f"Checkpoint saved — rerun anytime to pick up where you left off.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
