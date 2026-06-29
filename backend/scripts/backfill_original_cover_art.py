"""Backfill original_url for cover_art_cache rows that were manually overridden
before the original_url column existed.

For each row with manual_override=TRUE and original_url IS NULL, this script
queries iTunes for what the art would have been before the override and stores
the result in original_url without touching url or manual_override.

Idempotent — skips rows that already have original_url set.

Usage:
    python backend/scripts/backfill_original_cover_art.py
    python backend/scripts/backfill_original_cover_art.py --dry-run
    python backend/scripts/backfill_original_cover_art.py --sleep 4.0
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import httpx
from sqlalchemy import text

from app.db import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("backfill-art")

_UA = "the-record-backfill/1.0 (github.com/philipreese/the-record)"


async def _search_itunes(client: httpx.AsyncClient, artist: str, title: str) -> Optional[str]:
    try:
        r = await client.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "entity": "song", "media": "music", "limit": "5"},
            timeout=httpx.Timeout(10.0),
        )
        if r.status_code != 200:
            logger.warning("iTunes returned %d for %r / %r", r.status_code, artist, title)
            return None
        for result in r.json().get("results", []):
            url = result.get("artworkUrl100")
            if url:
                return url.replace("100x100bb", "300x300bb")
        return None
    except Exception as e:
        logger.warning("iTunes request failed for %r / %r: %s", artist, title, e)
        return None


def get_targets() -> list[tuple[str, str, str, str]]:
    """Return (artist_folded, title_folded, display_artist, display_title) for rows to backfill."""
    with get_engine().connect() as conn:
        keys = conn.execute(
            text("""
                SELECT artist_folded, title_folded
                FROM cover_art_cache
                WHERE manual_override AND original_url IS NULL
            """)
        ).fetchall()
        if not keys:
            return []

        results = []
        for af, tf in keys:
            row = conn.execute(
                text("""
                    SELECT artist, title FROM corrected_listens
                    WHERE LOWER(TRIM(artist)) = :af AND LOWER(TRIM(title)) = :tf
                    LIMIT 1
                """),
                {"af": af, "tf": tf},
            ).first()
            display_artist = row.artist if row else af
            display_title = row.title if row else tf
            results.append((af, tf, display_artist, display_title))
        return results


async def run(dry_run: bool, sleep_secs: float) -> None:
    targets = get_targets()
    if not targets:
        logger.info("No rows to backfill.")
        return

    logger.info("Backfilling %d row(s) with manual_override=TRUE and original_url IS NULL", len(targets))

    async with httpx.AsyncClient(headers={"User-Agent": _UA}) as client:
        for i, (af, tf, artist, title) in enumerate(targets, 1):
            logger.info("[%d/%d] %r / %r", i, len(targets), artist, title)
            url = await _search_itunes(client, artist, title)
            if url:
                logger.info("  -> %s", url)
            else:
                logger.info("  -> no result")

            if not dry_run:
                with get_engine().begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE cover_art_cache
                            SET original_url = :url
                            WHERE artist_folded = :af AND title_folded = :tf
                              AND original_url IS NULL
                        """),
                        {"url": url, "af": af, "tf": tf},
                    )

            if i < len(targets):
                time.sleep(sleep_secs)

    logger.info("Done.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing to DB")
    parser.add_argument("--sleep", type=float, default=3.0, help="Seconds between iTunes requests (default 3)")
    args = parser.parse_args()

    asyncio.run(run(dry_run=args.dry_run, sleep_secs=args.sleep))


if __name__ == "__main__":
    main()
