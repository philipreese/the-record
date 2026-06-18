import sys
import os
import time
import logging
import asyncio
import httpx

# Adjust path to import backend modules
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
sys.path.append(BACKEND_DIR)

from app.db import get_session, Listen
from sqlalchemy import select, update, and_

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("backfill")

# MusicBrainz User-Agent compliance guidelines
_UA = "the-record-backfill/1.0 (https://github.com/philipreese/the-record)"

async def query_musicbrainz(client: httpx.AsyncClient, artist: str, title: str):
    url = "https://musicbrainz.org/ws/2/recording"
    params = {
        "query": f'recording:"{title}" AND artist:"{artist}"',
        "fmt": "json",
        "limit": "1",
    }
    try:
        r = await client.get(url, params=params, headers={"User-Agent": _UA}, timeout=10.0)
        if r.status_code == 200:
            recordings = r.json().get("recordings", [])
            if recordings:
                rec = recordings[0]
                duration_ms = rec.get("length")
                duration_secs = int(duration_ms / 1000) if duration_ms else None
                
                album = None
                releases = rec.get("releases", [])
                if releases:
                    album = releases[0].get("title")
                return duration_secs, album
        else:
            logger.warning("MusicBrainz returned status %d for %r / %r", r.status_code, artist, title)
    except Exception as e:
        logger.error("Error querying MusicBrainz for %r / %r: %s", artist, title, e)
    return None, None

async def main():
    session = get_session()
    try:
        # Find unique tracks lacking duration or album
        logger.info("Querying unique tracks lacking metadata...")
        stmt = (
            select(Listen.artist, Listen.title)
            .where((Listen.duration_secs.is_(None)) | (Listen.album.is_(None)))
            .group_by(Listen.artist, Listen.title)
        )
        tracks = session.execute(stmt).all()
        logger.info("Found %d unique tracks to backfill", len(tracks))

        if not tracks:
            logger.info("All tracks have metadata! Nothing to do.")
            return

        async with httpx.AsyncClient() as client:
            for i, track in enumerate(tracks):
                artist, title = track.artist, track.title
                logger.info("[%d/%d] Fetching %r - %r", i + 1, len(tracks), artist, title)
                
                duration, album = await query_musicbrainz(client, artist, title)
                
                if duration or album:
                    # Update all listens matching this track
                    stmt_update = (
                        update(Listen)
                        .where(and_(Listen.artist == artist, Listen.title == title))
                        .values(
                            duration_secs=Listen.duration_secs if duration is None else duration,
                            album=Listen.album if album is None else album
                        )
                    )
                    session.execute(stmt_update)
                    session.commit()
                    logger.info("--> Backfilled: duration=%s, album=%r", duration, album)
                else:
                    logger.info("--> No metadata found")
                
                # Respect MusicBrainz rate limit: 1 request per second
                await asyncio.sleep(1.2)
                
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main())
