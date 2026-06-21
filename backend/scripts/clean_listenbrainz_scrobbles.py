#!/usr/bin/env python3
"""
ListenBrainz Scrobble Cleaner

Scans every scrobble on ListenBrainz, identifies entries with messy artist/title
names (featuring credits, country suffixes, video tags), deletes them, and
resubmits clean versions. Updates import_checkpoint.pkl so the checkpoint
stays authoritative after cleanup.

Run this AFTER:
  1. clean_database_metadata.py --confirm
  2. delete_listenbrainz.py
  3. import_listenbrainz.py

State is written to clean_lb_state.json after the scan phase so the script
can be safely interrupted and resumed without losing any listens.
"""

import os
import sys
import json
import time
import pickle
import urllib.request
import urllib.error
from datetime import datetime
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

sys.path.insert(0, BACKEND_DIR)
from app.utils import clean_artist, clean_title  # noqa: E402

load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

CHECKPOINT_FILE = os.path.join(BACKEND_DIR, "import_checkpoint.pkl")
STATE_FILE = os.path.join(SCRIPT_DIR, "clean_lb_state.json")
PAGE_SIZE = 1000


def safe_str(s: str | None) -> str:
    if s is None:
        return ""
    enc = sys.stdout.encoding or "utf-8"
    return s.encode(enc, errors="replace").decode(enc)


def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "rb") as f:
                cp = pickle.load(f)
                if isinstance(cp, dict) and "submitted" in cp:
                    return cp
        except Exception as e:
            print(f"Warning: could not read checkpoint ({e}). Starting fresh.")
    return {"submitted": set()}


def save_checkpoint(checkpoint: dict) -> None:
    with open(CHECKPOINT_FILE, "wb") as f:
        pickle.dump(checkpoint, f)


def load_state() -> list | None:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(entries: list) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def fetch_page(username: str, token: str, max_ts: int | None = None) -> dict:
    url = f"https://api.listenbrainz.org/1/user/{username}/listens?count={PAGE_SIZE}"
    if max_ts:
        url += f"&max_ts={max_ts}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Token {token}", "User-Agent": "the-record-lb-cleaner/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def api_delete(token: str, ts: int, msid: str) -> tuple[dict, object]:
    data = json.dumps({"listened_at": ts, "recording_msid": msid}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.listenbrainz.org/1/delete-listen",
        data=data,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": "the-record-lb-cleaner/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8")), r.headers


def api_submit(token: str, payload: list) -> tuple[dict, object]:
    data = json.dumps({"listen_type": "import", "payload": payload}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.listenbrainz.org/1/submit-listens",
        data=data,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": "the-record-lb-cleaner/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8")), r.headers


def _wait_for_rate_limit(headers: object) -> None:
    try:
        remaining = int(headers.get("X-RateLimit-Remaining", 50))  # type: ignore[union-attr]
        reset_in = float(headers.get("X-RateLimit-Reset-In", 0))   # type: ignore[union-attr]
        if remaining < 3:
            time.sleep(reset_in + 0.5)
    except Exception:
        pass


def scan_all_listens(username: str, token: str) -> list:
    """Page through all LB scrobbles and return dirty entries."""
    print("Phase 1: Scanning all ListenBrainz scrobbles...")
    dirty: list = []
    total_scanned = 0
    max_ts: int | None = None

    while True:
        res = None
        for attempt in range(3):
            try:
                res = fetch_page(username, token, max_ts=max_ts)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = float(e.headers.get("X-RateLimit-Reset-In", "5")) + 0.5
                    print(f"  Rate limited. Sleeping {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    print(f"  HTTP {e.code}. Retrying in 5s...")
                    time.sleep(5)
            except Exception as e:
                print(f"  Error: {e}. Retrying in 5s...")
                time.sleep(5)

        if res is None:
            print("  Could not fetch page after 3 attempts. Stopping scan early.")
            break

        listens = res.get("payload", {}).get("listens", [])
        if not listens:
            break

        for listen in listens:
            ts = listen.get("listened_at")
            meta = listen.get("track_metadata", {})
            raw_artist = meta.get("artist_name", "")
            raw_title = meta.get("track_name", "")
            msid = listen.get("recording_msid")
            if not ts or not raw_artist or not raw_title or not msid:
                continue
            c_artist = clean_artist(raw_artist)
            c_title = clean_title(raw_title)
            if c_artist != raw_artist or c_title != raw_title:
                dirty.append({
                    "ts": ts,
                    "msid": msid,
                    "raw_artist": raw_artist,
                    "raw_title": raw_title,
                    "clean_artist": c_artist,
                    "clean_title": c_title,
                })

        total_scanned += len(listens)
        oldest_ts = listens[-1].get("listened_at", 0)
        print(
            f"  Scanned {total_scanned:,} listens | {len(dirty)} dirty"
            f" | oldest: {datetime.fromtimestamp(oldest_ts).strftime('%Y-%m-%d')}"
        )

        if len(listens) < PAGE_SIZE:
            break
        max_ts = oldest_ts
        time.sleep(1.0)

    print(f"Scan complete. {total_scanned:,} scanned, {len(dirty)} dirty.")
    return dirty


def process_dirty_entries(dirty_entries: list, token: str, checkpoint: dict) -> int:
    """Delete each messy entry and immediately resubmit the clean version."""
    submitted_set: set = checkpoint["submitted"]
    total = len(dirty_entries)
    processed = 0
    print(f"\nPhase 2: Cleaning {total} entries (delete + resubmit)...")

    while dirty_entries:
        entry = dirty_entries[0]
        ts: int = entry["ts"]
        msid: str = entry["msid"]
        raw_artist: str = entry["raw_artist"]
        raw_title: str = entry["raw_title"]
        c_artist: str = entry["clean_artist"]
        c_title: str = entry["clean_title"]

        print(
            f"\n[{processed + 1}/{total}] {datetime.fromtimestamp(ts).strftime('%Y-%m-%d')}"
            f"  {safe_str(raw_artist)} - {safe_str(raw_title)}"
            f"\n          -> {safe_str(c_artist)} - {safe_str(c_title)}"
        )

        # Delete messy entry
        deleted = False
        while not deleted:
            try:
                res, headers = api_delete(token, ts, msid)
                _wait_for_rate_limit(headers)
                if res.get("status") == "ok":
                    deleted = True
                    print("  DELETE ok")
                else:
                    print(f"  DELETE returned unexpected response: {res}. Skipping entry.")
                    break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = float(e.headers.get("X-RateLimit-Reset-In", "5")) + 0.5
                    print(f"  Rate limited on delete. Sleeping {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    print(f"  HTTP {e.code} on delete. Skipping entry.")
                    break
            except Exception as e:
                print(f"  Error deleting: {e}. Retrying in 2s...")
                time.sleep(2)

        if not deleted:
            dirty_entries.pop(0)
            save_state(dirty_entries)
            continue

        # Remove dirty sig from checkpoint if it was there
        submitted_set.discard((ts, raw_artist, raw_title))

        # Resubmit clean version
        payload = [{
            "listened_at": ts,
            "track_metadata": {
                "artist_name": c_artist,
                "track_name": c_title,
                "additional_info": {"submission_client": "the-record-lb-cleaner"},
            },
        }]

        submitted = False
        while not submitted:
            try:
                res, headers = api_submit(token, payload)
                _wait_for_rate_limit(headers)
                if res.get("status") == "ok":
                    submitted = True
                    submitted_set.add((ts, c_artist, c_title))
                    print("  SUBMIT ok")
                else:
                    print(f"  SUBMIT failed: {res}. Retrying in 2s...")
                    time.sleep(2)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = float(e.headers.get("X-RateLimit-Reset-In", "5")) + 0.5
                    print(f"  Rate limited on submit. Sleeping {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    print(f"  HTTP {e.code} on submit. Retrying in 5s...")
                    time.sleep(5)
            except Exception as e:
                print(f"  Error submitting: {e}. Retrying in 2s...")
                time.sleep(2)

        processed += 1
        dirty_entries.pop(0)
        checkpoint["submitted"] = submitted_set
        save_checkpoint(checkpoint)
        save_state(dirty_entries)
        time.sleep(0.5)

    return processed


def main() -> None:
    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        print("Error: LISTENBRAINZ_USERNAME and LISTENBRAINZ_TOKEN must be set in .env")
        sys.exit(1)

    checkpoint = load_checkpoint()
    print(f"Checkpoint loaded: {len(checkpoint['submitted']):,} signatures.")

    dirty_entries = load_state()
    if dirty_entries is not None:
        print(f"Resuming from {STATE_FILE}: {len(dirty_entries)} entries remaining.")
    else:
        dirty_entries = scan_all_listens(LISTENBRAINZ_USERNAME, LISTENBRAINZ_TOKEN)
        if not dirty_entries:
            print("ListenBrainz is already clean. Nothing to do.")
            return
        save_state(dirty_entries)
        print(f"State saved. {len(dirty_entries)} dirty entries to process.")

    processed = process_dirty_entries(dirty_entries, LISTENBRAINZ_TOKEN, checkpoint)
    print(f"\nDone. Cleaned {processed} scrobble(s) on ListenBrainz.")

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


if __name__ == "__main__":
    main()
