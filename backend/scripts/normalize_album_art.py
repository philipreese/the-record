"""
Normalize cover_art_cache to use album-level artwork.

Source priority:
  1. MusicBrainz release-group search → Cover Art Archive front cover
     MusicBrainz tracks every release variant (standard, deluxe, instrumental,
     remastered) as distinct entries with separate CAA artwork. This is the
     most accurate source and what most streaming platforms use as their
     metadata backbone.
  2. iTunes Search API (entity=album, fallback entity=song)
     Broader mainstream coverage for albums not yet in CAA.

Run AFTER seed_cover_art.py has completed.

Usage:
    python backend/scripts/normalize_album_art.py
    python backend/scripts/normalize_album_art.py --dry-run 20
    python backend/scripts/normalize_album_art.py --reset
    python backend/scripts/normalize_album_art.py --itunes-sleep 3.0

Checkpoint: backend/scripts/normalize_album_art_checkpoint.json
Audit log:  backend/scripts/normalize_album_art_changes.log
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import httpx
from sqlalchemy import select, text, func, or_, and_

from app.db import get_engine, get_session, Listen, CoverArtCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("normalize-art")

OUTPUT_DIR = SCRIPTS_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CHECKPOINT_FILE = OUTPUT_DIR / "normalize_album_art_checkpoint.json"
CHANGES_LOG = OUTPUT_DIR / "normalize_album_art_changes.log"

# MusicBrainz requires a descriptive User-Agent with contact info.
_UA = "the-record/1.0 (pbreese42@gmail.com)"

_HARD_SKIP = frozenset([
    "live", "concert", "greatest hits", "best of", "compilation",
    "collection", "unplugged", "the singles",
    "karaoke", "tribute", "by request", "made famous", "backing track",
    "in the style of", "cover version", "originally performed",
])

# MusicBrainz rate limit: 1 req/sec for unauthenticated clients.
_MB_INTERVAL = 1.1
_last_mb_time: float = 0.0


# ── DB helpers ────────────────────────────────────────────────────────

def get_albums() -> list[tuple[str, str]]:
    """All distinct (album, primary_artist) pairs ordered by play count desc.

    Deduplicates by (album_folded, artist_folded) so same-named albums by
    different artists are treated as separate entries.
    """
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT album, artist, COUNT(*) AS plays "
                "FROM listens "
                "WHERE album IS NOT NULL AND trim(album) != '' "
                "GROUP BY lower(trim(album)), lower(trim(artist)) "
                "ORDER BY plays DESC"
            )
        ).fetchall()

    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for row in rows:
        key = (row.album.casefold().strip(), row.artist.casefold().strip())
        if key not in seen:
            seen.add(key)
            result.append((row.album, row.artist))
    return result


def get_tracks_for_album(album_name: str, artist_name: str) -> list[tuple[str, str]]:
    """Distinct (artist_folded, title_folded) pairs for this album+artist combo."""
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(Listen.artist, Listen.title)
            .where(
                func.lower(func.trim(Listen.album)) == album_name.casefold().strip(),
                func.lower(func.trim(Listen.artist)) == artist_name.casefold().strip(),
            )
            .distinct()
        ).fetchall()
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for artist, title in rows:
        key = (artist.casefold().strip(), title.casefold().strip())
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def get_current_art_urls(keys: list[tuple[str, str]]) -> dict[tuple[str, str], Optional[str]]:
    """Batch fetch current cover_art_cache URLs for the given (artist_f, title_f) keys."""
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
    return {(row.artist_folded, row.title_folded): row.url for row in rows}


def upsert_cover_art(artist_folded: str, title_folded: str, url: Optional[str]) -> None:
    session = get_session()
    try:
        obj = CoverArtCache(artist_folded=artist_folded, title_folded=title_folded, url=url)
        session.merge(obj)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _checkpoint_key(album: str, artist: str) -> str:
    return f"{album.casefold().strip()}||{artist.casefold().strip()}"


def load_checkpoint() -> set[str]:
    if CHECKPOINT_FILE.exists():
        return set(json.loads(CHECKPOINT_FILE.read_text()))
    return set()


def save_checkpoint(done: set[str]) -> None:
    CHECKPOINT_FILE.write_text(json.dumps(sorted(done)))


# ── MusicBrainz + Cover Art Archive ──────────────────────────────────

async def _mb_throttle() -> None:
    """Enforce MusicBrainz 1 req/sec rate limit."""
    global _last_mb_time
    elapsed = time.monotonic() - _last_mb_time
    wait = _MB_INTERVAL - elapsed
    if wait > 0:
        await asyncio.sleep(wait)
    _last_mb_time = time.monotonic()


def _caa_best_url(img: dict) -> Optional[str]:
    """Pick the best thumbnail size from a CAA image record."""
    th = img.get("thumbnails", {})
    url = th.get("500") or th.get("250") or th.get("large") or img.get("image") or None
    if url and url.startswith("http://"):
        url = "https://" + url[7:]
    return url


async def _get_caa_url(client: httpx.AsyncClient, rg_id: str) -> Optional[str]:
    """Fetch front cover URL from Cover Art Archive for a release group."""
    try:
        r = await client.get(
            f"https://coverartarchive.org/release-group/{rg_id}",
            timeout=httpx.Timeout(10.0),
            follow_redirects=True,
        )
        if r.status_code != 200:
            return None
        for img in r.json().get("images", []):
            if img.get("front"):
                return _caa_best_url(img)
        return None
    except Exception as e:
        logger.debug("CAA failed for %s: %s", rg_id, e)
        return None


async def _search_musicbrainz(
    client: httpx.AsyncClient,
    artist: str,
    album: str,
) -> Optional[str]:
    """Search MusicBrainz for a release group and return CAA front cover URL."""
    await _mb_throttle()
    try:
        query = f'artist:"{artist}" AND releasegroup:"{album}"'
        r = await client.get(
            "https://musicbrainz.org/ws/2/release-group",
            params={"query": query, "fmt": "json", "limit": "5"},
            timeout=httpx.Timeout(15.0),
        )
        if r.status_code != 200:
            logger.debug("MB returned %d for %r / %r", r.status_code, artist, album)
            return None

        rgs = r.json().get("release-groups", [])
        if not rgs:
            return None

        album_folded = album.casefold()
        # Exact title matches first, then fall through to fuzzy
        rgs_sorted = sorted(
            rgs, key=lambda rg: rg.get("title", "").casefold() != album_folded
        )

        for rg in rgs_sorted[:3]:
            url = await _get_caa_url(client, rg.get("id", ""))
            if url:
                return url
        return None
    except Exception as e:
        logger.debug("MB search failed for %r / %r: %s", artist, album, e)
        return None


# ── iTunes ────────────────────────────────────────────────────────────

def _pick_itunes_result(results: list[dict], album_name: str) -> Optional[str]:
    """Best artwork URL from iTunes results.

    Pass 1: exact collectionName match (case-insensitive).
    Pass 2: tier-aware selection — when the album is an instrumental release,
    prefer results whose collectionName also contains 'instrumental'; otherwise
    deprioritize them. Mirrors the logic in seed_cover_art.py so the normalization
    run doesn't overwrite correctly-seeded instrumental artwork.
    """
    album_folded = album_name.casefold()
    is_instrumental = "instrumental" in album_folded

    for r in results:
        if not r.get("artworkUrl100"):
            continue
        collection = r.get("collectionName", "").casefold()
        if any(kw in collection for kw in _HARD_SKIP):
            continue
        if collection == album_folded:
            return r["artworkUrl100"].replace("100x100bb", "300x300bb")

    tier1: list[dict] = []
    tier2: list[dict] = []
    for r in results:
        if not r.get("artworkUrl100"):
            continue
        collection = r.get("collectionName", "").casefold()
        if any(kw in collection for kw in _HARD_SKIP):
            continue
        if is_instrumental:
            (tier1 if "instrumental" in collection else tier2).append(r)
        else:
            (tier2 if "instrumental" in collection else tier1).append(r)

    chosen = next(iter(tier1 or tier2), None)
    if chosen:
        return chosen["artworkUrl100"].replace("100x100bb", "300x300bb")
    return None


async def _search_itunes(
    client: httpx.AsyncClient,
    artist: str,
    album: str,
) -> Optional[str]:
    """Return artwork URL from iTunes, trying entity=album then entity=song."""
    term = f"{artist} {album}"
    timeout = httpx.Timeout(10.0)
    try:
        r = await client.get(
            "https://itunes.apple.com/search",
            params={"term": term, "entity": "album", "media": "music", "limit": "5"},
            timeout=timeout,
        )
        if r.status_code == 200:
            url = _pick_itunes_result(r.json().get("results", []), album)
            if url:
                return url
        r2 = await client.get(
            "https://itunes.apple.com/search",
            params={"term": term, "entity": "song", "media": "music", "limit": "10"},
            timeout=timeout,
        )
        if r2.status_code == 200:
            return _pick_itunes_result(r2.json().get("results", []), album)
        return None
    except Exception as e:
        logger.debug("iTunes failed for %r / %r: %s", artist, album, e)
        return None


# ── Combined lookup ───────────────────────────────────────────────────

async def _find_album_art(
    client: httpx.AsyncClient,
    artist: str,
    album: str,
    itunes_sleep: float,
) -> tuple[Optional[str], str]:
    """Return (url, source). Tries MB+CAA first, falls back to iTunes."""
    url = await _search_musicbrainz(client, artist, album)
    if url:
        return url, "mb+caa"
    await asyncio.sleep(itunes_sleep)
    url = await _search_itunes(client, artist, album)
    return url, ("itunes" if url else "not found")


# ── Main ──────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--itunes-sleep", type=float, default=3.0,
        help="Seconds to wait before an iTunes fallback request (default 3.0). "
             "Not used when MusicBrainz finds the album.",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear checkpoint and audit log, start from scratch",
    )
    parser.add_argument(
        "--dry-run", type=int, metavar="N", default=0,
        help="Preview first N albums without writing anything. "
             "Shows both MB+CAA and iTunes results for comparison.",
    )
    args = parser.parse_args()

    if args.reset:
        for f in (CHECKPOINT_FILE, CHANGES_LOG):
            if f.exists():
                f.unlink()
        logger.info("Checkpoint and audit log cleared.")

    albums = get_albums()
    done = load_checkpoint()
    remaining = [
        (album, artist) for album, artist in albums
        if _checkpoint_key(album, artist) not in done
    ]

    if args.dry_run:
        sample = remaining[: args.dry_run]
        if not sample:
            logger.info("Nothing to preview.")
            return
        logger.info("=== DRY RUN: previewing %d albums (no writes) ===", len(sample))
        async with httpx.AsyncClient(headers={"User-Agent": _UA}) as client:
            for album, artist in sample:
                mb_url = await _search_musicbrainz(client, artist, album)
                await asyncio.sleep(args.itunes_sleep)
                itunes_url = await _search_itunes(client, artist, album)
                winning_url = mb_url or itunes_url
                source = "mb+caa" if mb_url else ("itunes" if itunes_url else "not found")
                tracks = get_tracks_for_album(album, artist)
                current = get_current_art_urls(tracks)
                would_change = sum(1 for u in current.values() if u != winning_url)
                print(f"\n  album:   {album!r}")
                print(f"  artist:  {artist}")
                print(f"  mb+caa:  {mb_url or '(not found)'}")
                print(f"  itunes:  {itunes_url or '(not found)'}")
                print(f"  winner:  {source}")
                print(f"  tracks:  {len(tracks)}  |  unique current: {len(set(current.values()))}  |  would change: {would_change}")
        logger.info("=== DRY RUN complete -- nothing written ===")
        return

    logger.info(
        "Albums: %d total | %d done | %d remaining",
        len(albums), len(done), len(remaining),
    )
    if not remaining:
        logger.info("Nothing to do. Use --reset to re-run.")
        return

    mb_found = itunes_found = not_found = already_consistent = total_tracks_updated = 0
    start_time = time.monotonic()
    log_mode = "a" if CHECKPOINT_FILE.exists() and not args.reset else "w"

    with open(CHANGES_LOG, log_mode, encoding="utf-8") as log_file:
        log_file.write(
            f"\n=== run started: {time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"({len(remaining)} albums) ===\n"
        )
        log_file.flush()

        async with httpx.AsyncClient(headers={"User-Agent": _UA}) as client:
            for i, (album, artist) in enumerate(remaining, 1):
                url, source = await _find_album_art(client, artist, album, args.itunes_sleep)
                ck = _checkpoint_key(album, artist)

                if url:
                    if source == "mb+caa":
                        mb_found += 1
                    else:
                        itunes_found += 1
                    tracks = get_tracks_for_album(album, artist)
                    current = get_current_art_urls(tracks)
                    changed = 0
                    for af, tf in tracks:
                        old_url = current.get((af, tf))
                        if old_url != url:
                            upsert_cover_art(af, tf, url)
                            log_file.write(
                                f"[ART] {af} -- {tf}  (album: {album!r}, source: {source})\n"
                                f"  old: {old_url!r}\n  new: {url!r}\n"
                            )
                            changed += 1
                    log_file.flush()
                    total_tracks_updated += changed
                    if changed == 0:
                        already_consistent += 1
                    status = f"[{source}]  {changed} updated, {len(tracks) - changed} unchanged"
                else:
                    not_found += 1
                    status = "[not found]"

                done.add(ck)

                elapsed = time.monotonic() - start_time
                rate = i / elapsed if elapsed > 0 else 0.001
                eta_secs = (len(remaining) - i) / rate
                eta_str = (
                    f"{int(eta_secs // 3600):02d}:"
                    f"{int((eta_secs % 3600) // 60):02d}:"
                    f"{int(eta_secs % 60):02d}"
                )
                print(
                    f"[{i:>5}/{len(remaining)}] {album[:40]:<40}  {status:<45}  ETA {eta_str}"
                )

                if i % 10 == 0:
                    save_checkpoint(done)

    save_checkpoint(done)
    elapsed_total = time.monotonic() - start_time
    logger.info(
        "Done. mb+caa: %d | itunes: %d | not found: %d | "
        "already consistent: %d | tracks updated: %d | elapsed: %.1f min",
        mb_found, itunes_found, not_found, already_consistent,
        total_tracks_updated, elapsed_total / 60,
    )
    logger.info("Audit log: %s", CHANGES_LOG)
    logger.info("Next: run mirror_to_prod.py --confirm to sync updated art to prod.")


if __name__ == "__main__":
    asyncio.run(main())
