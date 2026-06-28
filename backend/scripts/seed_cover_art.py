"""
Seed cover_art_cache, listens.duration_secs, and listens.album from iTunes
for every unique (artist, title) pair in the listens table.

Replaces fuzzy MusicBrainz backfill values with a single consistent iTunes
source, establishing a trustworthy baseline before the manual correction UI
lands.

Usage:
    python backend/scripts/seed_cover_art.py
    python backend/scripts/seed_cover_art.py --dry-run 5
    python backend/scripts/seed_cover_art.py --sleep 2.0
    python backend/scripts/seed_cover_art.py --reset

Checkpoint: backend/scripts/seed_cover_art_checkpoint.json
Audit log:  backend/scripts/seed_cover_art_changes.log

Run with the dev server STOPPED -- both share iTunes' ~20 req/min rate limit.
"""

import argparse
import asyncio
import json
import logging
import os
import random
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
from sqlalchemy import select, text

from app.db import get_engine, get_session, Listen, CoverArtCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("seed-art")

CHECKPOINT_FILE = SCRIPTS_DIR / "seed_cover_art_checkpoint.json"
CHANGES_LOG = SCRIPTS_DIR / "seed_cover_art_changes.log"

_UA = "the-record-seed/1.0 (github.com/philipreese/the-record)"

# Never use results whose collectionName contains these -- fundamentally different
# recordings (live, karaoke, tribute) or not real albums (compilations, hits).
_HARD_SKIP = frozenset([
    "live", "concert", "greatest hits", "best of", "compilation",
    "collection", "unplugged", "the singles",
    "karaoke", "tribute", "by request", "made famous", "backing track",
    "in the style of", "cover version", "originally performed",
])

# Same recording, variant packaging -- accept only if no standard edition exists.
_SOFT_SKIP = frozenset([
    "deluxe", "- ep", "(ep)", "- single", "(single)",
    "bonus edition", "commentary",
    "instrumental",
    "vsq", "string quartet",
])

# If the iTunes result duration differs from the existing value by more than this,
# treat it as a wrong-track match and discard the result entirely.
_DURATION_TOLERANCE_SECS = 30


def _pick_result(
    results: list[dict],
    existing_duration_secs: Optional[int] = None,
    title: str = "",
) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """Return (art_url, duration_secs, collection_name) from the best iTunes result.

    Priority:
      tier1 -- not hard/soft skipped, duration matches existing (or no existing to compare)
      tier2 -- soft skipped (deluxe / EP / single), duration ok
      give up -- all results are hard-skipped or duration-mismatched; return (None, None, None)

    Special case: if the track title itself contains "instrumental", the preference is
    inverted — instrumental album collections become tier1 and standard editions tier2.
    This handles albums where the instrumental version has an identical duration to the
    standard version (e.g. Sleep Token), so duration alone can't differentiate them.
    """
    tier1: list[dict] = []
    tier2: list[dict] = []
    is_instrumental_track = "instrumental" in title.lower()

    for r in results:
        if not r.get("artworkUrl100"):
            continue

        collection = r.get("collectionName", "").lower()

        if any(kw in collection for kw in _HARD_SKIP):
            continue

        duration_ms = r.get("trackTimeMillis")
        itunes_dur = round(duration_ms / 1000) if duration_ms else None
        duration_mismatch = (
            existing_duration_secs is not None
            and itunes_dur is not None
            and abs(existing_duration_secs - itunes_dur) > _DURATION_TOLERANCE_SECS
        )
        if duration_mismatch:
            continue

        if is_instrumental_track:
            # Prefer the instrumental album; accept standard edition as fallback.
            if "instrumental" in collection:
                tier1.append(r)
            else:
                tier2.append(r)
        else:
            if any(kw in collection for kw in _SOFT_SKIP):
                tier2.append(r)
            else:
                tier1.append(r)

    chosen = next(iter(tier1 or tier2), None)
    if not chosen:
        return None, None, None

    raw_url = chosen.get("artworkUrl100", "")
    art_url = raw_url.replace("100x100bb", "300x300bb") if raw_url else None

    duration_ms = chosen.get("trackTimeMillis")
    duration_secs = round(duration_ms / 1000) if duration_ms else None

    return art_url or None, duration_secs, chosen.get("collectionName") or None


async def _search_itunes(
    client: httpx.AsyncClient,
    artist: str,
    title: str,
    existing_duration_secs: Optional[int] = None,
) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """Return (art_url, duration_secs, collection_name) from iTunes, or (None, None, None)."""
    try:
        r = await client.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "entity": "song", "media": "music", "limit": "10"},
            timeout=httpx.Timeout(10.0),
        )
        if r.status_code != 200:
            logger.warning("iTunes returned %d for %r / %r", r.status_code, artist, title)
            return None, None, None
        return _pick_result(r.json().get("results", []), existing_duration_secs, title)
    except Exception as e:
        logger.warning("iTunes request failed for %r / %r: %s", artist, title, e)
        return None, None, None


def get_all_tracks() -> list[tuple[str, str]]:
    """All distinct (artist_folded, title_folded) pairs from listens, deduped in Python.

    Python casefold() handles Unicode correctly; SQLite lower() is ASCII-only.
    """
    with get_engine().connect() as conn:
        rows = conn.execute(select(Listen.artist, Listen.title).distinct()).fetchall()
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for artist, title in rows:
        key = (artist.casefold().strip(), title.casefold().strip())
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def get_current_metadata() -> dict[tuple[str, str], tuple[Optional[int], Optional[str]]]:
    """First (duration_secs, album) per folded key -- snapshot for the audit log."""
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(Listen.artist, Listen.title, Listen.duration_secs, Listen.album)
        ).fetchall()
    result: dict[tuple[str, str], tuple[Optional[int], Optional[str]]] = {}
    for artist, title, dur, alb in rows:
        key = (artist.casefold().strip(), title.casefold().strip())
        if key not in result:
            result[key] = (dur, alb)
    return result


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


def update_listens_metadata(
    artist_folded: str,
    title_folded: str,
    duration_secs: Optional[int],
    album: Optional[str],
) -> None:
    """Overwrite duration_secs and album for every listen matching this folded key."""
    updates: dict = {}
    if duration_secs is not None:
        updates["duration_secs"] = duration_secs
    if album is not None:
        updates["album"] = album
    if not updates:
        return

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    params = {**updates, "af": artist_folded, "tf": title_folded}
    with get_engine().begin() as conn:
        conn.execute(
            text(
                f"UPDATE listens SET {set_clause}"
                " WHERE lower(trim(artist)) = :af AND lower(trim(title)) = :tf"
            ),
            params,
        )


def load_checkpoint() -> set[str]:
    if CHECKPOINT_FILE.exists():
        return set(json.loads(CHECKPOINT_FILE.read_text()))
    return set()


def save_checkpoint(done: set[str]) -> None:
    CHECKPOINT_FILE.write_text(json.dumps(sorted(done)))


def _log_change(log_file, kind: str, artist: str, title: str, old, new) -> None:
    if old == new:
        return
    log_file.write(f"[{kind}] {artist} -- {title}\n  old: {old!r}\n  new: {new!r}\n")
    log_file.flush()


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--sleep", type=float, default=3.0,
        help="Seconds between iTunes requests (default 3.0, ~20 req/min)",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear checkpoint and audit log, start from scratch",
    )
    parser.add_argument(
        "--dry-run", type=int, metavar="N", default=0,
        help="Preview N unprocessed tracks via iTunes without writing anything",
    )
    parser.add_argument(
        "--random", action="store_true",
        help="With --dry-run: pick N tracks at random instead of the first N",
    )
    parser.add_argument(
        "--reprocess-filter", metavar="SUBSTR",
        help="Re-seed tracks whose title contains SUBSTR, bypassing the checkpoint",
    )
    args = parser.parse_args()

    if args.dry_run and args.reset:
        parser.error("--dry-run and --reset cannot be used together")

    if args.reset:
        for f in (CHECKPOINT_FILE, CHANGES_LOG):
            if f.exists():
                f.unlink()
        logger.info("Checkpoint and audit log cleared.")

    tracks = get_all_tracks()
    done = load_checkpoint()
    current_meta = get_current_metadata()

    if args.dry_run:
        rf = (args.reprocess_filter or "").lower()
        pool = [t for t in tracks if rf and rf in t[1] or f"{t[0]}|{t[1]}" not in done]
        sample = random.sample(pool, min(args.dry_run, len(pool))) if args.random else pool[: args.dry_run]
        if not sample:
            logger.info("Dry run: no unprocessed tracks to preview.")
            return
        logger.info("=== DRY RUN: previewing %d tracks (no writes) ===", len(sample))
        async with httpx.AsyncClient(headers={"User-Agent": _UA}) as client:
            for af, tf in sample:
                old_dur, old_alb = current_meta.get((af, tf), (None, None))
                art_url, duration_secs, album = await _search_itunes(client, af, tf, old_dur)
                print(f"\n  track:    {af} -- {tf}")
                print(f"  art:      {art_url or '(not found)'}")
                print(f"  album:    {old_alb!r}  ->  {album!r}")
                print(f"  duration: {old_dur}s  ->  {duration_secs if duration_secs is not None else '(not found)'}s")
                if args.dry_run > 1:
                    await asyncio.sleep(args.sleep)
        logger.info("=== DRY RUN complete -- nothing written ===")
        return

    total = len(tracks)
    reprocess_filter = (args.reprocess_filter or "").lower()
    if reprocess_filter:
        # Bypass checkpoint for tracks whose title matches the filter.
        remaining = [
            (af, tf) for af, tf in tracks
            if reprocess_filter in tf or f"{af}|{tf}" not in done
        ]
        logger.info("Reprocess filter %r active.", reprocess_filter)
    else:
        remaining = [(af, tf) for af, tf in tracks if f"{af}|{tf}" not in done]

    logger.info(
        "Unique tracks: %d | Already done: %d | Remaining: %d",
        total, len(done), len(remaining),
    )
    if not remaining:
        logger.info("Nothing to do. Use --reset to re-seed from scratch.")
        return

    found = not_found = 0
    start_time = time.monotonic()
    log_mode = "a" if CHECKPOINT_FILE.exists() and not args.reset else "w"

    with open(CHANGES_LOG, log_mode, encoding="utf-8") as log_file:
        log_file.write(
            f"\n=== run started: {time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"({len(remaining)} tracks) ===\n"
        )
        log_file.flush()

        async with httpx.AsyncClient(headers={"User-Agent": _UA}) as client:
            for i, (af, tf) in enumerate(remaining, 1):
                old_dur, old_alb = current_meta.get((af, tf), (None, None))
                art_url, duration_secs, album = await _search_itunes(client, af, tf, old_dur)

                # Always write to cover_art_cache -- None marks the track as attempted
                # so the live server doesn't retry it on every request.
                upsert_cover_art(af, tf, art_url)

                if art_url is not None:
                    _log_change(log_file, "DURATION", af, tf, old_dur, duration_secs)
                    _log_change(log_file, "ALBUM", af, tf, old_alb, album)
                    update_listens_metadata(af, tf, duration_secs, album)
                    found += 1
                    album_display = (album or "?")[:35]
                    status = f"found   ({album_display}, {duration_secs}s)"
                else:
                    not_found += 1
                    status = "not found"

                done.add(f"{af}|{tf}")

                elapsed = time.monotonic() - start_time
                rate = i / elapsed if elapsed > 0 else 0.001
                eta_secs = (len(remaining) - i) / rate
                eta_str = (
                    f"{int(eta_secs // 3600):02d}:"
                    f"{int((eta_secs % 3600) // 60):02d}:"
                    f"{int(eta_secs % 60):02d}"
                )

                print(
                    f"[{i:>6}/{len(remaining)}] "
                    f"{af[:30]:<30} -- {tf[:30]:<30}  "
                    f"{status:<50}  ETA {eta_str}"
                )

                if i % 10 == 0:
                    save_checkpoint(done)

                if i < len(remaining):
                    await asyncio.sleep(args.sleep)

    save_checkpoint(done)
    elapsed_total = time.monotonic() - start_time
    logger.info(
        "Done. Found: %d | Not found: %d | Elapsed: %.1f min",
        found, not_found, elapsed_total / 60,
    )
    logger.info("Audit log written to: %s", CHANGES_LOG)

    all_processed = done >= {f"{af}|{tf}" for af, tf in tracks}
    if all_processed:
        logger.info(
            "All tracks processed. Next: run mirror_to_prod.py --confirm to sync prod."
        )


if __name__ == "__main__":
    asyncio.run(main())
