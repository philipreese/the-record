from sqlalchemy import text
from app.db import get_engine

# Canonical artist name corrections.
# Keys are the wrong names as submitted by scrobblers; values are the correct names.
# To add a correction: insert a new entry here and deploy — both local and prod DBs
# are updated on next startup. No migration needed.
ARTIST_CORRECTIONS: dict[str, str] = {
    "Invent Animate": "Invent, Animate",
}


def sync_artist_corrections() -> None:
    """Sync ARTIST_CORRECTIONS into the artist_corrections table.

    Upserts all entries from the dict and removes any rows whose wrong_name
    is no longer present. Safe to call on every startup.
    """
    with get_engine().begin() as conn:
        if ARTIST_CORRECTIONS:
            placeholders = ", ".join(f":k{i}" for i in range(len(ARTIST_CORRECTIONS)))
            conn.execute(
                text(f"DELETE FROM artist_corrections WHERE wrong_name NOT IN ({placeholders})"),
                {f"k{i}": k for i, k in enumerate(ARTIST_CORRECTIONS)},
            )
            for wrong, correct in ARTIST_CORRECTIONS.items():
                conn.execute(
                    text(
                        "INSERT INTO artist_corrections (wrong_name, correct_name)"
                        " VALUES (:w, :c)"
                        " ON CONFLICT (wrong_name) DO UPDATE SET correct_name = excluded.correct_name"
                    ),
                    {"w": wrong, "c": correct},
                )
        else:
            conn.execute(text("DELETE FROM artist_corrections"))
