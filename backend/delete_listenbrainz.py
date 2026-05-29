#!/usr/bin/env python3
"""
ListenBrainz History Cleaner
Deletes plays from ListenBrainz that have been removed from backend/merged_history.json.
Uses an optimized window-paging algorithm to fetch and delete entries efficiently.
"""

import os
import json
import sys
import time
import pickle
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from dotenv import load_dotenv

def safe_str(s):
    """Encode a string safely for the current terminal, replacing un-encodable chars."""
    if s is None:
        return ""
    return s.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")

load_dotenv(dotenv_path=".env")

LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

CHECKPOINT_FILE = os.path.join("backend", "import_checkpoint.pkl")
MERGED_HISTORY_FILE = os.path.join("backend", "merged_history.json")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "rb") as f:
                checkpoint = pickle.load(f)
                if isinstance(checkpoint, dict) and "submitted" in checkpoint:
                    return checkpoint
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
    return {"submitted": set()}

def save_checkpoint(checkpoint):
    try:
        with open(CHECKPOINT_FILE, "wb") as f:
            pickle.dump(checkpoint, f)
    except Exception as e:
        print(f"Error saving checkpoint: {e}")

def delete_listen(token, listened_at, recording_msid):
    """Call POST /1/delete-listen to schedule a deletion on ListenBrainz."""
    url = "https://api.listenbrainz.org/1/delete-listen"
    body = {
        "listened_at": listened_at,
        "recording_msid": recording_msid
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": "the-record-cleaner/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8")), r.headers

def fetch_listens_page(username, token, max_ts=None):
    """Fetch user listens up to count=100 and older than max_ts."""
    url = f"https://api.listenbrainz.org/1/user/{username}/listens?count=100"
    if max_ts:
        url += f"&max_ts={max_ts}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {token}",
            "User-Agent": "the-record-cleaner/1.0"
        }
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8")), r.headers

def main():
    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        print("Error: ListenBrainz credentials missing.")
        print("Please configure LISTENBRAINZ_USERNAME and LISTENBRAINZ_TOKEN in your .env file.")
        sys.exit(1)

    checkpoint = load_checkpoint()
    submitted_set = checkpoint["submitted"]
    print(f"Loaded checkpoint with {len(submitted_set):,} submitted signatures.")

    if not os.path.exists(MERGED_HISTORY_FILE):
        print(f"Error: {MERGED_HISTORY_FILE} not found.")
        sys.exit(1)

    with open(MERGED_HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)

    # Build keep set of signatures (unix_ts, artist, title)
    keep_set = set()
    for entry in history:
        sig = (entry["unix_ts"], entry["artist"], entry["title"])
        keep_set.add(sig)

    # Signatures to delete: in checkpoint but not in current clean history
    to_delete_sigs = submitted_set - keep_set
    print(f"Found {len(to_delete_sigs):,} plays to delete from ListenBrainz.")
    
    if not to_delete_sigs:
        print("No plays need to be deleted! Checkpoint is in sync with history.")
        return

    # Index deletion signatures by timestamp for quick lookup
    # key: timestamp -> list of (artist, title, sig)
    to_delete_by_time = {}
    for sig in to_delete_sigs:
        ts = sig[0]
        to_delete_by_time.setdefault(ts, []).append((sig[1].lower().strip(), sig[2].lower().strip(), sig))

    # Sort all target timestamps descending
    target_timestamps = sorted(to_delete_by_time.keys(), reverse=True)
    total_to_delete = len(to_delete_sigs)
    deleted_count = 0

    print("Starting optimized deletion process...")
    
    while target_timestamps:
        # Take the most recent target timestamp to query around it
        curr_ts = target_timestamps[0]
        print(f"\nFetching page around timestamp {curr_ts} ({datetime.fromtimestamp(curr_ts).strftime('%Y-%m-%d %H:%M:%S')})...")
        
        # Request listens starting slightly after the target timestamp to catch it
        max_ts = curr_ts + 5
        try:
            res, headers = fetch_listens_page(LISTENBRAINZ_USERNAME, LISTENBRAINZ_TOKEN, max_ts=max_ts)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                reset_in = e.headers.get("X-RateLimit-Reset-In", "5")
                sleep_val = float(reset_in) + 1.0
                print(f"  ⚠ Rate limited (429). Sleeping for {sleep_val:.1f}s...")
                time.sleep(sleep_val)
                continue
            else:
                print(f"  HTTP Error {e.code}: {e.read().decode('utf-8')}. Retrying in 5s...")
                time.sleep(5)
                continue
        except Exception as e:
            print(f"  Network error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        listens = res.get("payload", {}).get("listens", [])
        if not listens:
            print("  No listens returned in this range. Removing targets >= current timestamp.")
            target_timestamps = [t for t in target_timestamps if t < curr_ts]
            continue

        # Find the oldest timestamp in the returned batch
        returned_timestamps = [l.get("listened_at") for l in listens if l.get("listened_at")]
        min_ts = min(returned_timestamps) if returned_timestamps else curr_ts
        print(f"  Received {len(listens)} listens in range [{min_ts} -> {max(returned_timestamps)}].")

        # Scan the batch for matches
        deleted_in_batch = 0
        for listen in listens:
            ts = listen.get("listened_at")
            meta = listen.get("track_metadata", {})
            art = meta.get("artist_name", "").lower().strip()
            tit = meta.get("track_name", "").lower().strip()
            msid = listen.get("recording_msid")

            if ts in to_delete_by_time and msid:
                # Find matching signature
                match_sig = None
                for target_art, target_tit, sig in to_delete_by_time[ts]:
                    if target_art == art and target_tit == tit:
                        match_sig = sig
                        break
                
                if match_sig:
                    print(f"  Deleting: [{datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')}] {safe_str(meta.get('artist_name'))} - {safe_str(meta.get('track_name'))}...")
                    retry_del = True
                    while retry_del:
                        try:
                            del_res, del_headers = delete_listen(LISTENBRAINZ_TOKEN, ts, msid)
                            if del_res.get("status") == "ok":
                                deleted_count += 1
                                deleted_in_batch += 1
                                
                                # Remove from checkpoint and local tracking
                                submitted_set.discard(match_sig)
                                checkpoint["submitted"] = submitted_set
                                save_checkpoint(checkpoint)
                                
                                # Remove from to_delete_by_time mapping
                                to_delete_by_time[ts] = [x for x in to_delete_by_time[ts] if x[2] != match_sig]
                                if not to_delete_by_time[ts]:
                                    del to_delete_by_time[ts]
                                    
                                print("    Success.")
                                retry_del = False
                                time.sleep(0.3)  # Small gap to respect rate limits
                            else:
                                print(f"    Failed to delete: {del_res}")
                                retry_del = False
                        except urllib.error.HTTPError as de:
                            if de.code == 429:
                                reset_in = de.headers.get("X-RateLimit-Reset-In", "5")
                                sleep_val = float(reset_in) + 1.0
                                print(f"    ⚠ Deletion rate-limited (429). Sleeping {sleep_val:.1f}s...")
                                time.sleep(sleep_val)
                            else:
                                print(f"    HTTP Error on deletion: {de.code}")
                                retry_del = False
                        except Exception as de:
                            print(f"    Network error on deletion: {de}. Retrying...")
                            time.sleep(2)

        print(f"  Batch complete. Deleted {deleted_in_batch} listens. Progress: {deleted_count}/{total_to_delete} deleted.")
        
        # Remove all target timestamps that fell inside this batch range
        # We also remove curr_ts just in case to avoid infinite loop
        target_timestamps = [t for t in target_timestamps if t < min_ts and t != curr_ts]
        
        # Small gap before next batch request
        time.sleep(1.0)

    print(f"\nClean up complete. Deleted {deleted_count} listens from ListenBrainz.")
    print("Checkpoint has been synchronized with the clean history.")

if __name__ == "__main__":
    main()
