import asyncio
import logging
from collections import OrderedDict
from typing import Any, Optional

import httpx
from starlette.concurrency import run_in_threadpool

import app.repository as repo

logger = logging.getLogger(__name__)

UA = "the-record-dashboard/1.0 (https://github.com/philipreese/the-record)"


class _BoundedCache(OrderedDict):
    """Insertion-ordered dict that evicts the oldest entry once it exceeds ``maxsize``.

    Keeps the per-process art caches from growing without bound over a long-running
    process (one entry per distinct track otherwise lives forever).
    """

    def __init__(self, maxsize: int) -> None:
        super().__init__()
        self._maxsize = maxsize

    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self:
            super().__delitem__(key)
        super().__setitem__(key, value)
        while len(self) > self._maxsize:
            self.popitem(last=False)


_ART_CACHE_MAX = 2048
# Per-process cache so we only pay the MB/CAA lookup cost once per track per session.
# Both successful and failed lookups (after _MAX_ART_ATTEMPTS) are stored to prevent
# hitting rate limits and causing slow HTTP cascades on consecutive polls.
cover_art_cache: "OrderedDict[tuple[str, str], Optional[str]]" = _BoundedCache(_ART_CACHE_MAX)
_cover_art_attempts: "OrderedDict[tuple[str, str], int]" = _BoundedCache(_ART_CACHE_MAX)
_MAX_ART_ATTEMPTS = 3
# Tracks keys currently being resolved in background to prevent duplicate tasks.
_art_in_flight: set[tuple[str, str]] = set()
# Keys with manually set art that the background resolver must never overwrite.
manual_override_art_keys: set[tuple[str, str]] = set()
# One background iTunes request at a time with a post-request sleep keeps us
# well under Apple's undocumented rate limit (~20 req/min observed in practice).
_art_semaphore = asyncio.Semaphore(1)


async def _get_caa_direct_url(client: httpx.AsyncClient, release_mbid: str) -> Optional[str]:
    """Resolve a direct archive.org image URL from Cover Art Archive (avoids the redirect)."""
    try:
        r = await client.get(
            f"https://coverartarchive.org/release/{release_mbid}",
            headers={"User-Agent": UA},
            timeout=httpx.Timeout(2.0),
            follow_redirects=True,
        )
        if r.status_code == 200:
            images = r.json().get("images", [])
            front = next((img for img in images if img.get("front")), images[0] if images else None)
            if front:
                return front.get("thumbnails", {}).get("250") or front.get("image")
    except Exception:
        logger.debug("CAA direct lookup failed for release_mbid=%s", release_mbid, exc_info=True)
    return None


async def _get_caa_release_group_url(client: httpx.AsyncClient, release_group_mbid: str) -> Optional[str]:
    """Resolve cover art via release group MBID — wider CAA coverage than per-release lookup."""
    try:
        r = await client.get(
            f"https://coverartarchive.org/release-group/{release_group_mbid}",
            headers={"User-Agent": UA},
            timeout=httpx.Timeout(2.0),
            follow_redirects=True,
        )
        if r.status_code == 200:
            images = r.json().get("images", [])
            front = next((img for img in images if img.get("front")), images[0] if images else None)
            if front:
                return front.get("thumbnails", {}).get("250") or front.get("image")
    except Exception:
        logger.debug("CAA release-group lookup failed for release_group_mbid=%s", release_group_mbid, exc_info=True)
    return None


async def search_cover_art_itunes(
    client: httpx.AsyncClient, artist: str, title: str
) -> Optional[str]:
    """Primary cover art lookup via iTunes Search API — single request, high coverage, no auth needed."""
    try:
        r = await client.get(
            "https://itunes.apple.com/search",
            params={"term": f"{artist} {title}", "entity": "song", "media": "music", "limit": "5"},
            timeout=httpx.Timeout(5.0),
        )
        if r.status_code != 200:
            logger.debug("iTunes search returned %d for %r / %r", r.status_code, artist, title)
            return None
        for result in r.json().get("results", []):
            url = result.get("artworkUrl100")
            if url:
                return url.replace("100x100bb", "300x300bb")
    except Exception as e:
        logger.debug("iTunes cover art lookup failed for %r / %r: %s(%s)", artist, title, type(e).__name__, e)
    return None


def art_key(artist: str, title: str) -> tuple[str, str]:
    """Case-folded cache key so LB API casing and DB casing resolve to the same entry."""
    return (artist.casefold().strip(), title.casefold().strip())


async def _resolve_cover_art(
    client: httpx.AsyncClient,
    artist: str,
    title: str,
    release_mbid: Optional[str],
    recording_mbid: Optional[str],
    release_group_mbid: Optional[str] = None,
) -> Optional[str]:
    """Resolve cover art URL with caching. Both successes and failures are cached to avoid HTTP cascades."""
    cache_key = art_key(artist, title)
    if cache_key in cover_art_cache:
        return cover_art_cache[cache_key]
    attempts = _cover_art_attempts.get(cache_key, 0)
    if attempts >= _MAX_ART_ATTEMPTS:
        logger.debug("Cover art suppressed for %r / %r after %d failed attempts", artist, title, attempts)
        return None

    _cover_art_attempts[cache_key] = attempts + 1

    url: Optional[str] = None
    # Tier 1: direct CAA lookup when we already have a release MBID (playing-now provides one)
    if release_mbid:
        url = await _get_caa_direct_url(client, release_mbid)
    if not url and release_group_mbid:
        url = await _get_caa_release_group_url(client, release_group_mbid)
    # Tier 2: iTunes — single request, high coverage, no rate limit concerns
    if not url:
        url = await search_cover_art_itunes(client, artist, title)

    if url:
        cover_art_cache[cache_key] = url
    else:
        logger.debug(
            "Cover art resolution failed for %r / %r (attempt %d/%d); release_mbid=%s recording_mbid=%s release_group_mbid=%s",
            artist, title, attempts + 1, _MAX_ART_ATTEMPTS, release_mbid, recording_mbid, release_group_mbid,
        )
        if attempts + 1 >= _MAX_ART_ATTEMPTS:
            cover_art_cache[cache_key] = None
    return url


async def bg_resolve_art(
    artist: str,
    title: str,
    release_mbid: Optional[str],
    recording_mbid: Optional[str],
    release_group_mbid: Optional[str],
) -> None:
    """Resolve cover art in the background and persist the result to the DB cache."""
    cache_key = art_key(artist, title)
    if cache_key in manual_override_art_keys:
        _art_in_flight.discard(cache_key)
        return
    try:
        async with _art_semaphore:
            async with httpx.AsyncClient(headers={"User-Agent": UA}) as bg:
                await _resolve_cover_art(bg, artist, title, release_mbid, recording_mbid, release_group_mbid)
            if cache_key in cover_art_cache:
                await run_in_threadpool(
                    repo.upsert_cover_art, cache_key[0], cache_key[1], cover_art_cache.get(cache_key)
                )
            # Hold the semaphore through the sleep so concurrent tasks queue up
            # and we stay under iTunes' rate limit (~20 req/min).
            await asyncio.sleep(3.0)
    except Exception:
        logger.debug("Background cover art resolution failed for %r / %r", artist, title, exc_info=True)
    finally:
        _art_in_flight.discard(cache_key)


def schedule_art(coro) -> None:
    """Schedule a background art task if the event loop is running."""
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        pass


def populate_cover_art(listens: list) -> None:
    """Fill cover_art_url from in-process cache then DB for each listen."""
    mem_misses: list[tuple] = []
    for listen in listens:
        key = art_key(listen.artist, listen.title)
        if key in cover_art_cache:
            listen.cover_art_url = cover_art_cache[key]
        else:
            mem_misses.append((listen, key))
    if mem_misses:
        db_hits = repo.get_cover_art_batch([k for _, k in mem_misses])
        for listen, key in mem_misses:
            if key in db_hits:
                url, is_override = db_hits[key]
                cover_art_cache[key] = url
                if is_override:
                    manual_override_art_keys.add(key)
                listen.cover_art_url = url


def set_art_in_flight(key: tuple[str, str], value: bool) -> None:
    """Add or remove a key from the in-flight set."""
    if value:
        _art_in_flight.add(key)
    else:
        _art_in_flight.discard(key)


def is_art_in_flight(key: tuple[str, str]) -> bool:
    return key in _art_in_flight
