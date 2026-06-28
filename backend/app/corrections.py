from sqlalchemy import text
from app.db import get_engine
from app.db_helpers import IS_POSTGRES

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


# Canonical album name corrections.
# Keys are wrong names as submitted by scrobblers; values are the correct names.
ALBUM_CORRECTIONS: dict[str, str] = {
    # "Wrong Album Name": "Correct Album Name",
}


def sync_album_corrections() -> None:
    """Sync ALBUM_CORRECTIONS into the album_corrections table.

    Upserts all entries from the dict and removes any rows whose wrong_album
    is no longer present. Safe to call on every startup.
    """
    with get_engine().begin() as conn:
        if ALBUM_CORRECTIONS:
            placeholders = ", ".join(f":k{i}" for i in range(len(ALBUM_CORRECTIONS)))
            conn.execute(
                text(f"DELETE FROM album_corrections WHERE wrong_album NOT IN ({placeholders})"),
                {f"k{i}": k for i, k in enumerate(ALBUM_CORRECTIONS)},
            )
            for wrong, correct in ALBUM_CORRECTIONS.items():
                conn.execute(
                    text(
                        "INSERT INTO album_corrections (wrong_album, correct_album)"
                        " VALUES (:w, :c)"
                        " ON CONFLICT (wrong_album) DO UPDATE SET correct_album = excluded.correct_album"
                    ),
                    {"w": wrong, "c": correct},
                )
        else:
            conn.execute(text("DELETE FROM album_corrections"))


def apply_album_corrections() -> int:
    """Bulk-update listens whose album name matches a row in album_corrections.

    Returns the number of rows updated. Safe to call after every sync.
    """
    with get_engine().begin() as conn:
        if IS_POSTGRES:
            result = conn.execute(text("""
                UPDATE listens
                SET album = ac.correct_album
                FROM album_corrections ac
                WHERE LOWER(TRIM(listens.album)) = LOWER(TRIM(ac.wrong_album))
            """))
        else:
            result = conn.execute(text("""
                UPDATE listens
                SET album = (
                    SELECT correct_album FROM album_corrections
                    WHERE LOWER(TRIM(wrong_album)) = LOWER(TRIM(listens.album))
                    LIMIT 1
                )
                WHERE LOWER(TRIM(album)) IN (SELECT LOWER(TRIM(wrong_album)) FROM album_corrections)
            """))
        return result.rowcount
