"""
Reconcile ListenBrainz vs local DB.

Phases (run in order):
  python reconcile_lb.py            -- report only (fixed Unicode comparison)
  python reconcile_lb.py --upload   -- upload DB-only plays to LB
  python reconcile_lb.py --dedup    -- remove duplicate listens from LB

Uses the cache written by diagnose_lb_gap.py; run that first if cache is missing.
"""

import os, sys, json, time, sqlite3
from pathlib import Path
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

TOKEN    = os.environ["LISTENBRAINZ_TOKEN"]
USERNAME = os.environ["LISTENBRAINZ_USERNAME"]
DB_PATH  = ROOT / "backend" / "history.db"
CACHE    = ROOT / "backend" / "scripts" / "diagnose_lb_cache.json"

HEADERS = {"Authorization": f"Token {TOKEN}"}


def make_key(ts, artist, title):
    return (ts, artist.strip().lower(), title.strip().lower())


def load_lb_cache():
    if not CACHE.exists():
        print("ERROR: Cache not found. Run diagnose_lb_gap.py first.")
        sys.exit(1)
    print(f"Loading LB cache...")
    listens = json.loads(CACHE.read_text(encoding="utf-8"))
    print(f"  {len(listens)} total LB listens")
    return listens


def load_db_rows():
    print("Loading DB rows...")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT unix_ts, artist, title FROM listens").fetchall()
    conn.close()
    print(f"  {len(rows)} DB rows")
    return rows


def build_lb_structures(listens):
    """Returns key_set, key_to_listens (for finding duplicates)."""
    key_to_listens = {}
    for entry in listens:
        meta = entry.get("track_metadata", {})
        ts   = entry.get("listened_at")
        artist = meta.get("artist_name", "")
        title  = meta.get("track_name", "")
        if not ts or not artist or not title:
            continue
        key = make_key(ts, artist, title)
        key_to_listens.setdefault(key, []).append(entry)
    return set(key_to_listens.keys()), key_to_listens


def build_db_key_set(rows):
    return {make_key(ts, artist, title) for ts, artist, title in rows}


def report(lb_keys, db_keys, key_to_listens, db_rows):
    on_lb_not_db = lb_keys - db_keys
    on_db_not_lb = db_keys - lb_keys
    duplicates   = {k: v for k, v in key_to_listens.items() if len(v) > 1}

    print(f"\n--- counts (Unicode-correct comparison) ---")
    print(f"LB unique keys : {len(lb_keys)}")
    print(f"DB rows        : {len(db_keys)}")
    print(f"On LB not in DB: {len(on_lb_not_db)}")
    print(f"In DB not on LB: {len(on_db_not_lb)}")
    print(f"LB duplicates  : {len(duplicates)} keys, "
          f"{sum(len(v)-1 for v in duplicates.values())} extra entries to remove")

    if on_lb_not_db:
        print(f"\n--- On LB but not in DB ({len(on_lb_not_db)} total) ---")
        for ts, artist, title in sorted(on_lb_not_db, reverse=True):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            print(f"  {dt}  {artist!r:35s}  {title!r}")

    if on_db_not_lb:
        print(f"\n--- In DB but not on LB (up to 15) ---")
        for ts, artist, title in sorted(on_db_not_lb, reverse=True)[:15]:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            print(f"  {dt}  {artist!r:35s}  {title!r}")

    return on_lb_not_db, on_db_not_lb, duplicates


def upload_to_lb(on_db_not_lb, db_rows):
    """Upload plays that are in DB but not on LB."""
    if not on_db_not_lb:
        print("Nothing to upload.")
        return

    # Build a lookup so we can get the original (un-lowercased) values
    row_by_key = {make_key(ts, a, t): (ts, a, t) for ts, a, t in db_rows}

    url = f"https://api.listenbrainz.org/1/submit-listens"
    batch = []
    submitted = 0

    for key in sorted(on_db_not_lb, key=lambda k: k[0]):
        ts, artist, title = row_by_key[key]
        batch.append({
            "listened_at": ts,
            "track_metadata": {
                "artist_name": artist,
                "track_name": title,
            }
        })
        if len(batch) == 100:
            _submit_batch(url, batch)
            submitted += len(batch)
            print(f"  Submitted {submitted}/{len(on_db_not_lb)}...")
            batch = []
            time.sleep(1)

    if batch:
        _submit_batch(url, batch)
        submitted += len(batch)

    print(f"Upload complete. Submitted {submitted} plays to LB.")


def _submit_batch(url, batch):
    payload = {"listen_type": "import", "payload": batch}
    for attempt in range(5):
        try:
            r = httpx.post(url, headers=HEADERS, json=payload, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get("X-RateLimit-Reset-In", 10))
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait + 1)
                continue
            r.raise_for_status()
            return
        except Exception as e:
            if attempt < 4:
                print(f"  Error ({e.__class__.__name__}), retry {attempt+1}/4...")
                time.sleep(5)
            else:
                raise


def dedup_lb(duplicates):
    """Delete extra copies of duplicate LB listens, keeping one per key."""
    if not duplicates:
        print("No duplicates to remove.")
        return

    total_extras = sum(len(v) - 1 for v in duplicates.values())
    print(f"Removing {total_extras} duplicate LB listens...")

    url = f"https://api.listenbrainz.org/1/delete-listen"
    removed = 0

    for key, entries in duplicates.items():
        # Keep first entry (lowest listened_at order doesn't matter — just keep one)
        extras = entries[1:]
        for entry in extras:
            ts   = entry.get("listened_at")
            msid = entry.get("recording_msid") or (
                entry.get("track_metadata", {})
                    .get("additional_info", {})
                    .get("recording_msid")
            )
            if not ts or not msid:
                print(f"  Skipping entry missing msid: ts={ts}")
                continue

            for attempt in range(5):
                try:
                    r = httpx.post(url, headers=HEADERS,
                                   json={"listened_at": ts, "recording_msid": msid},
                                   timeout=30)
                    if r.status_code == 429:
                        wait = int(r.headers.get("X-RateLimit-Reset-In", 10))
                        time.sleep(wait + 1)
                        continue
                    r.raise_for_status()
                    removed += 1
                    break
                except Exception as e:
                    if attempt < 4:
                        time.sleep(3)
                    else:
                        print(f"  Failed to delete ts={ts}: {e}")

            if removed % 50 == 0 and removed > 0:
                print(f"  Removed {removed}/{total_extras}...")
            time.sleep(0.5)

    print(f"Dedup complete. Removed {removed} duplicate entries from LB.")


def delete_lb_dirty(on_lb_not_db, key_to_listens):
    """Delete LB listens that are not in the local DB."""
    if not on_lb_not_db:
        print("Nothing to delete.")
        return

    url = "https://api.listenbrainz.org/1/delete-listen"
    removed = 0
    total = len(on_lb_not_db)

    for key in sorted(on_lb_not_db, key=lambda k: k[0]):
        for entry in key_to_listens.get(key, []):
            ts   = entry.get("listened_at")
            msid = entry.get("recording_msid") or (
                entry.get("track_metadata", {})
                    .get("additional_info", {})
                    .get("recording_msid")
            )
            if not ts or not msid:
                print(f"  Skipping (no msid): ts={ts}")
                continue
            for attempt in range(5):
                try:
                    r = httpx.post(url, headers=HEADERS,
                                   json={"listened_at": ts, "recording_msid": msid},
                                   timeout=30)
                    if r.status_code == 429:
                        wait = int(r.headers.get("X-RateLimit-Reset-In", 10))
                        time.sleep(wait + 1)
                        continue
                    r.raise_for_status()
                    removed += 1
                    break
                except Exception as e:
                    if attempt < 4:
                        time.sleep(3)
                    else:
                        print(f"  Failed ts={ts}: {e}")
            if removed % 20 == 0 and removed > 0:
                print(f"  Deleted {removed}/{total}...")
            time.sleep(0.3)

    print(f"Delete complete. Removed {removed} dirty entries from LB.")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true",
                        help="Upload DB-only plays to LB")
    parser.add_argument("--delete", action="store_true",
                        help="Delete LB-only plays (dirty scrobbles not in DB)")
    parser.add_argument("--dedup", action="store_true",
                        help="Remove duplicate listens from LB")
    args = parser.parse_args()

    listens  = load_lb_cache()
    db_rows  = load_db_rows()
    lb_keys, key_to_listens = build_lb_structures(listens)
    db_keys  = build_db_key_set(db_rows)

    on_lb_not_db, on_db_not_lb, duplicates = report(
        lb_keys, db_keys, key_to_listens, db_rows
    )

    if args.upload:
        print(f"\n--- Uploading {len(on_db_not_lb)} plays to LB ---")
        upload_to_lb(on_db_not_lb, db_rows)

    if args.delete:
        print(f"\n--- Deleting {len(on_lb_not_db)} dirty LB entries ---")
        delete_lb_dirty(on_lb_not_db, key_to_listens)

    if args.dedup:
        print(f"\n--- Deduplicating LB ---")
        dedup_lb(duplicates)


if __name__ == "__main__":
    main()
