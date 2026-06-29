from ._base import (
    Optional,
    select,
    or_,
    and_,
    text,
    get_engine,
    CoverArtCache,
    IS_POSTGRES,
)


def get_all_cover_art() -> dict[tuple[str, str], tuple[Optional[str], bool]]:
    """Load every cover art entry from the persistent DB cache.

    Returns a dict mapping (artist_folded, title_folded) to (url, manual_override).
    """
    with get_engine().connect() as conn:
        rows = conn.execute(select(CoverArtCache)).fetchall()
        return {
            (row.artist_folded, row.title_folded): (row.url, bool(row.manual_override))
            for row in rows
        }


def get_cover_art_batch(keys: list[tuple[str, str]]) -> dict[tuple[str, str], tuple[Optional[str], bool]]:
    """Look up a batch of (artist_folded, title_folded) keys from the DB cache.

    Returns only keys that exist in the DB (absent = never attempted).
    Each value is (url, manual_override).
    """
    if not keys:
        return {}
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(CoverArtCache).where(
                or_(*[
                    and_(CoverArtCache.artist_folded == k[0], CoverArtCache.title_folded == k[1])
                    for k in keys
                ])
            )
        ).fetchall()
    return {
        (row.artist_folded, row.title_folded): (row.url, bool(row.manual_override))
        for row in rows
    }


def upsert_cover_art(
    artist_folded: str,
    title_folded: str,
    url: Optional[str],
    manual_override: bool = False,
) -> None:
    """Insert or update a cover art URL in the persistent cache.

    manual_override=True marks the entry so background resolvers skip it.
    This flag is sticky — once True, subsequent calls with manual_override=False
    leave it True to prevent auto-resolution from overwriting user-set art.
    """
    with get_engine().begin() as conn:
        if IS_POSTGRES:
            conn.execute(
                text(
                    "INSERT INTO cover_art_cache (artist_folded, title_folded, url, original_url, manual_override)"
                    " VALUES (:af, :tf, :url, :url, :mo)"
                    " ON CONFLICT (artist_folded, title_folded) DO UPDATE SET"
                    "   url = CASE WHEN cover_art_cache.manual_override THEN cover_art_cache.url ELSE excluded.url END,"
                    "   original_url = COALESCE(cover_art_cache.original_url, excluded.url),"
                    "   manual_override = cover_art_cache.manual_override OR excluded.manual_override"
                ),
                {"af": artist_folded, "tf": title_folded, "url": url, "mo": manual_override},
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO cover_art_cache (artist_folded, title_folded, url, original_url, manual_override)"
                    " VALUES (:af, :tf, :url, :url, :mo)"
                    " ON CONFLICT (artist_folded, title_folded) DO UPDATE SET"
                    "   url = CASE WHEN cover_art_cache.manual_override THEN cover_art_cache.url ELSE excluded.url END,"
                    "   original_url = COALESCE(cover_art_cache.original_url, excluded.url),"
                    "   manual_override = MAX(cover_art_cache.manual_override, excluded.manual_override)"
                ),
                {"af": artist_folded, "tf": title_folded, "url": url, "mo": int(manual_override)},
            )
