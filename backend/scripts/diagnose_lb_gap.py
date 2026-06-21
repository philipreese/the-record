"""
Quick diagnostic: find what's on LB but not in the local DB.
Fetches all LB listens and diffs against DB by (ts, artist, title) key.
"""

import os, sys, pickle, time, sqlite3, json
from pathlib import Path
from datetime import datetime, timezone

import httpx as requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

TOKEN    = os.environ["LISTENBRAINZ_TOKEN"]
USERNAME = os.environ["LISTENBRAINZ_USERNAME"]
DB_PATH  = ROOT / "backend" / "history.db"
CKPT     = ROOT / "backend" / "import_checkpoint.pkl"

HEADERS  = {"Authorization": f"Token {TOKEN}"}
CACHE    = ROOT / "backend" / "scripts" / "diagnose_lb_cache.json"

def lb_listen_key(entry):
    meta = entry.get("track_metadata", {})
    return (
        entry.get("listened_at"),
        (meta.get("artist_name") or "").strip().lower(),
        (meta.get("track_name")  or "").strip().lower(),
    )

def fetch_all_lb():
    if CACHE.exists():
        print(f"Loading LB listens from cache ({CACHE.name})...")
        return json.loads(CACHE.read_text(encoding="utf-8"))
    print("Fetching all LB listens (this will take a few minutes)...")
    listens = []
    url = f"https://api.listenbrainz.org/1/user/{USERNAME}/listens"
    params = {"count": 100}
    page = 0
    while True:
        for attempt in range(8):
            try:
                r = requests.get(url, headers=HEADERS, params=params, timeout=30)
                if r.status_code == 429:
                    wait = int(r.headers.get("X-RateLimit-Reset-In", 10))
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait + 1)
                    continue
                r.raise_for_status()
                break
            except Exception as e:
                if attempt < 7:
                    print(f"  Connection error ({e.__class__.__name__}), retry {attempt+1}/7...")
                    time.sleep(5)
                else:
                    raise
        batch = r.json()["payload"]["listens"]
        if not batch:
            break
        listens.extend(batch)
        page += 1
        if page % 10 == 0:
            print(f"  {len(listens)} fetched so far...")
        oldest_ts = batch[-1]["listened_at"]
        params["max_ts"] = oldest_ts - 1
        time.sleep(1.0)
    print(f"  Total fetched from LB: {len(listens)}")
    CACHE.write_text(json.dumps(listens), encoding="utf-8")
    print(f"  Cached to {CACHE.name}")
    return listens

def fetch_db_keys():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT unix_ts, LOWER(TRIM(artist)), LOWER(TRIM(title)) FROM listens"
    ).fetchall()
    conn.close()
    return set(rows)

def main():
    lb_listens = fetch_all_lb()
    print(f"\nBuilding LB key set...")
    lb_keys = {lb_listen_key(e) for e in lb_listens}

    print(f"Loading DB...")
    db_keys = fetch_db_keys()

    print(f"\n--- counts ---")
    print(f"LB listens fetched : {len(lb_listens)}")
    print(f"LB unique keys     : {len(lb_keys)}")
    print(f"DB rows            : {len(db_keys)}")

    on_lb_not_db = lb_keys - db_keys
    on_db_not_lb = db_keys - lb_keys

    print(f"\nOn LB but NOT in DB : {len(on_lb_not_db)}")
    print(f"In DB but NOT on LB : {len(on_db_not_lb)}")

    if on_lb_not_db:
        print(f"\n--- Sample of plays on LB but not in DB (up to 20) ---")
        sample = sorted(on_lb_not_db, key=lambda x: x[0] or 0, reverse=True)[:20]
        for ts, artist, title in sample:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "?"
            line = f"  {dt}  {artist!r:35s}  {title!r}"
            print(line.encode("utf-8", errors="replace").decode("utf-8"))

    if on_db_not_lb:
        print(f"\n--- Sample of plays in DB but not on LB (up to 20) ---")
        sample = sorted(on_db_not_lb, key=lambda x: x[0] or 0, reverse=True)[:20]
        for ts, artist, title in sample:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "?"
            line = f"  {dt}  {artist!r:35s}  {title!r}"
            print(line.encode("utf-8", errors="replace").decode("utf-8"))

if __name__ == "__main__":
    main()
