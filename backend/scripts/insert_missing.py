"""Insert plays that are legitimately missing from DB, then submit them to LB."""
import os, sys, sqlite3, json, time
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

TOKEN = os.environ["LISTENBRAINZ_TOKEN"]
DB_PATH = ROOT / "backend" / "history.db"

# Entries to insert: (unix_ts, artist, title)
# cul/de-sac corrected to proper metadata; others taken from LB cache as-is.
ENTRIES = [
    (1781715982, "Imminence",          "Cul-de-Sac"),          # was CUL / De-Sac on LB
    (1780774068, "Allison Eide",        "HIPS"),
    (1681544378, "Justin Starling",     "Way It Goes"),
    (1679476792, "Dance Gavin Dance",   "Death of a Strawberry (Tree City Sessions)"),
    (1679476149, "Dance Gavin Dance",   "We Own the Night (Tree City Sessions)"),
    (1669177108, "Scale the Summit",    "Dont Mind Me"),
    (1655331312, "Joel Corry",          "Head & Heart (VIP Mix)"),
]

def insert_db():
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    for ts, artist, title in ENTRIES:
        existing = conn.execute(
            "SELECT id FROM listens WHERE unix_ts=? AND artist=? AND title=?",
            (ts, artist, title)
        ).fetchone()
        if existing:
            print(f"  Already in DB: {artist} / {title}")
        else:
            conn.execute(
                "INSERT INTO listens (unix_ts, artist, title, source) VALUES (?, ?, ?, ?)",
                (ts, artist, title, "listenbrainz_sync")
            )
            inserted += 1
            print(f"  Inserted: {artist} / {title}")
    conn.commit()
    conn.close()
    print(f"DB: inserted {inserted} rows")

def submit_lb():
    payload = [
        {"listened_at": ts, "track_metadata": {"artist_name": a, "track_name": t}}
        for ts, a, t in ENTRIES
    ]
    r = httpx.post(
        "https://api.listenbrainz.org/1/submit-listens",
        headers={"Authorization": f"Token {TOKEN}"},
        json={"listen_type": "import", "payload": payload},
        timeout=30,
    )
    r.raise_for_status()
    print(f"LB: submitted {len(payload)} plays")

if __name__ == "__main__":
    print("--- Inserting into DB ---")
    insert_db()
    print("\n--- Submitting to LB ---")
    submit_lb()
    print("\nDone.")
