#!/usr/bin/env python3
"""
ListenBrainz History Importer
Imports the consolidated history from backend/merged_history.json to ListenBrainz.
Supports batching, checkpointing, and dynamic rate-limiting.
"""

import os
import json
import sys
import time
import pickle
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from dotenv import load_dotenv
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

CHECKPOINT_FILE = os.path.join(PROJECT_ROOT, "backend", "import_checkpoint.pkl")
BATCH_SIZE = 1000  # ListenBrainz API maximum per import request
DEFAULT_SLEEP = 1.0

# ── Checkpoint Helpers ────────────────────────────────────────────────────────

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "rb") as f:
                checkpoint = pickle.load(f)
                # Check for old/new schema compatibility
                if isinstance(checkpoint, dict) and "submitted" in checkpoint:
                    return checkpoint
        except Exception as e:
            print(f"Warning: Could not read checkpoint file ({e}). Starting fresh.")
    return {"submitted": set()}

def save_checkpoint(checkpoint):
    try:
        with open(CHECKPOINT_FILE, "wb") as f:
            pickle.dump(checkpoint, f)
    except Exception as e:
        print(f"Warning: Could not save checkpoint ({e}).")

# ── API Submission ────────────────────────────────────────────────────────────

def submit_batch(token, payload_list):
    """
    Submits a list of listens to the ListenBrainz API.
    Returns (status_dict, headers) on success, or raises an HTTPError.
    """
    url = "https://api.listenbrainz.org/1/submit-listens"
    body = {
        "listen_type": "import",
        "payload": payload_list
    }
    data = json.dumps(body).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": "the-record-importer/1.0"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req) as r:
        response_data = json.loads(r.read().decode("utf-8"))
        return response_data, r.headers

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        print("Error: ListenBrainz credentials missing.")
        print("Please set LISTENBRAINZ_USERNAME and LISTENBRAINZ_TOKEN in your .env file.")
        sys.exit(1)

    history_path = os.path.join(PROJECT_ROOT, "backend", "merged_history.json")
    if not os.path.exists(history_path):
        print(f"Error: Consolidated history file not found at '{history_path}'")
        print("Please run backend/merge_history.py first to generate the file.")
        sys.exit(1)

    print(f"Loading {history_path}...")
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        print(f"Error reading history file: {e}")
        sys.exit(1)

    total_entries = len(history)
    print(f"Loaded {total_entries:,} total entries from history.")

    # Load checkpoint
    checkpoint = load_checkpoint()
    submitted_set = checkpoint["submitted"]
    print(f"Loaded checkpoint. {len(submitted_set):,} entries already imported.")

    # Load existing database plays to avoid importing duplicates
    db_plays = {}  # key: (artist, title) -> list of unix_ts
    db_path = os.path.join(PROJECT_ROOT, "backend", "history.db")
    if os.path.exists(db_path):
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT artist, title, unix_ts FROM listens")
            for artist, title, unix_ts in cursor.fetchall():
                key = (artist.lower().strip(), title.lower().strip())
                if key not in db_plays:
                    db_plays[key] = []
                db_plays[key].append(unix_ts)
            conn.close()
            print(f"Loaded {sum(len(v) for v in db_plays.values()):,} existing listens from local database to prevent duplicates.")
        except Exception as e:
            print(f"Warning: Could not read local database to check duplicates ({e}).")

    # Filter to pending entries
    pending = []
    skipped_duplicates = 0
    for entry in history:
        sig = (entry["unix_ts"], entry["artist"], entry["title"])
        if sig in submitted_set:
            continue

        # Check if the song was already scrobbled within 60 seconds in the database
        key = (entry["artist"].lower().strip(), entry["title"].lower().strip())
        is_already_scrobbled = False
        if key in db_plays:
            for db_ts in db_plays[key]:
                if abs(db_ts - entry["unix_ts"]) <= 60:
                    is_already_scrobbled = True
                    break

        if is_already_scrobbled:
            submitted_set.add(sig)
            skipped_duplicates += 1
        else:
            pending.append(entry)

    if skipped_duplicates > 0:
        print(f"Skipped {skipped_duplicates:,} entries that are already in the database (e.g. scrobbled by Pano Scrobbler).")
        checkpoint["submitted"] = submitted_set
        save_checkpoint(checkpoint)

    print(f"Pending entries to import: {len(pending):,}")
    if not pending:
        print("All entries already imported! Nothing to do.")
        return

    # Sort pending chronologically just in case
    pending.sort(key=lambda e: e["unix_ts"])

    # Prepare batches
    batches = [pending[i:i + BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
    print(f"Split into {len(batches)} batches of up to {BATCH_SIZE} listens.")

    # Start import
    success_count = 0
    sleep_time = DEFAULT_SLEEP

    for i, batch in enumerate(batches):
        print(f"\nSubmitting batch {i + 1}/{len(batches)} ({len(batch)} items)...")
        
        # Build payload
        payload = []
        for entry in batch:
            service = "music.youtube.com" if entry.get("source") == "youtube_music" else "last.fm"
            payload.append({
                "listened_at": entry["unix_ts"],
                "track_metadata": {
                    "artist_name": entry["artist"],
                    "track_name": entry["title"],
                    "additional_info": {
                        "music_service": service,
                        "submission_client": "the-record-consolidator"
                    }
                }
            })

        retry = True
        while retry:
            try:
                res, headers = submit_batch(LISTENBRAINZ_TOKEN, payload)
                
                # Check status
                if res.get("status") == "ok":
                    print("  Batch accepted by ListenBrainz.")
                    success_count += len(batch)
                    
                    # Update checkpoint
                    for entry in batch:
                        sig = (entry["unix_ts"], entry["artist"], entry["title"])
                        submitted_set.add(sig)
                    checkpoint["submitted"] = submitted_set
                    save_checkpoint(checkpoint)
                    
                    # Inspect Rate Limit Headers
                    limit = headers.get("X-RateLimit-Limit")
                    remaining = headers.get("X-RateLimit-Remaining")
                    reset_in = headers.get("X-RateLimit-Reset-In")
                    
                    if remaining is not None and reset_in is not None:
                        rem_val = int(remaining)
                        reset_val = float(reset_in)
                        print(f"  Rate Limit Status: {rem_val}/{limit} remaining. Reset in {reset_val:.1f}s.")
                        
                        # Dynamic backoff if we're running out of budget
                        if rem_val <= 2:
                            sleep_time = reset_val + 0.5
                            print(f"  ⚠ Approaching rate limit. Increasing sleep to {sleep_time:.1f}s.")
                        else:
                            sleep_time = DEFAULT_SLEEP
                    else:
                        sleep_time = DEFAULT_SLEEP
                    
                    retry = False
                else:
                    print(f"  Error: Submission not ok. Response: {res}")
                    retry = False
                    
            except urllib.error.HTTPError as e:
                # Handle rate limiting specifically
                if e.code == 429:
                    reset_in = e.headers.get("X-RateLimit-Reset-In", "60")
                    sleep_val = float(reset_in) + 1.0
                    print(f"  ⚠ Rate limited (429). Sleeping for {sleep_val:.1f}s before retrying...")
                    time.sleep(sleep_val)
                else:
                    print(f"  HTTP Error {e.code}: {e.read().decode('utf-8')}")
                    retry = False
            except Exception as e:
                print(f"  Network error: {e}")
                print("  Sleeping 5 seconds before retrying...")
                time.sleep(5)

        # Sleep between batches
        if i < len(batches) - 1:
            time.sleep(sleep_time)

    print(f"\nImport process completed. Successfully imported {success_count:,} new plays.")
    print("Checkpoint saved. If any errors occurred, run the script again to resume.")

if __name__ == "__main__":
    main()
