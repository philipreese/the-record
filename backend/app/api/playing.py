import logging
from typing import Optional

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import app.repository as repo
from app.lb_client import get_lb_client
from app.playing_now_sse import broadcaster as pn_broadcaster
from app.schemas import LastPlayedEntry, ListenEntry, PlayingNowResponse
from app.services.cover_art import (
    UA,
    art_key,
    bg_resolve_art,
    cover_art_cache,
    is_art_in_flight,
    schedule_art,
    search_cover_art_itunes,
    set_art_in_flight,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/playing-now", response_model=PlayingNowResponse)
async def get_playing_now() -> PlayingNowResponse:
    """Fetch the currently playing track from ListenBrainz, or the most recent listen if nothing is playing."""
    from app.sync import LISTENBRAINZ_USERNAME, LISTENBRAINZ_TOKEN

    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        rows = repo.get_recent_listens(limit=1)
        if not rows:
            return PlayingNowResponse(is_playing=False)
        r = rows[0]
        return PlayingNowResponse(
            is_playing=False,
            last_played=LastPlayedEntry(artist=r.artist, title=r.title, unix_ts=r.unix_ts),
        )

    lb_url = f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/playing-now"
    lb_headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "User-Agent": UA,
    }
    try:
        client = get_lb_client()
        res = await client.get(lb_url, headers=lb_headers, timeout=httpx.Timeout(4.0))
        res.raise_for_status()

        listens = res.json().get("payload", {}).get("listens", [])
        if not listens:
            # Nothing playing — get the most recent DB listen, then fetch its MBIDs from
            # LB's listens endpoint so we can do a proper CAA lookup instead of text search.
            rows = repo.get_recent_listens(limit=1)
            if not rows:
                return PlayingNowResponse(is_playing=False)
            r = rows[0]

            # Fast-path: return immediately on cache hit.
            cache_key = art_key(r.artist, r.title)
            if cache_key in cover_art_cache:
                return PlayingNowResponse(
                    is_playing=False,
                    last_played=LastPlayedEntry(
                        artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                        cover_art_url=cover_art_cache[cache_key],
                    ),
                )
            # Cache miss: resolve inline — iTunes answers in ~100ms so the added
            # latency is negligible compared to the LB API call above.
            async with httpx.AsyncClient(headers={"User-Agent": UA}) as art_client:
                np_art = await search_cover_art_itunes(art_client, r.artist, r.title)
            cover_art_cache[cache_key] = np_art
            await run_in_threadpool(repo.upsert_cover_art, cache_key[0], cache_key[1], np_art)
            return PlayingNowResponse(
                is_playing=False,
                last_played=LastPlayedEntry(
                    artist=r.artist, title=r.title, unix_ts=r.unix_ts, cover_art_url=np_art
                ),
            )

        meta = listens[0].get("track_metadata", {})
        artist = meta.get("artist_name")
        title = meta.get("track_name")
        release = meta.get("release_name")
        mbid_mapping = meta.get("mbid_mapping", {})
        release_mbid = mbid_mapping.get("caa_release_mbid") or mbid_mapping.get("release_mbid")
        recording_mbid = mbid_mapping.get("recording_mbid")
        release_group_mbid = mbid_mapping.get("release_group_mbid")

        cover_art_url: Optional[str] = None
        if artist and title:
            np_key = art_key(artist, title)
            if np_key in cover_art_cache:
                cover_art_url = cover_art_cache[np_key]
            else:
                async with httpx.AsyncClient(headers={"User-Agent": UA}) as art_client:
                    cover_art_url = await search_cover_art_itunes(art_client, artist, title)
                cover_art_cache[np_key] = cover_art_url
                await run_in_threadpool(repo.upsert_cover_art, np_key[0], np_key[1], cover_art_url)

        return PlayingNowResponse(
            is_playing=bool(artist and title),
            artist=artist,
            title=title,
            release=release,
            cover_art_url=cover_art_url,
        )
    except Exception as e:
        logger.warning("LB playing-now request failed (%s: %s); falling back to last DB listen", type(e).__name__, e)
        rows = repo.get_recent_listens(limit=1)
        if not rows:
            return PlayingNowResponse(is_playing=False)
        r = rows[0]
        cache_key = art_key(r.artist, r.title)
        cached_art = cover_art_cache.get(cache_key)
        if cache_key not in cover_art_cache and not is_art_in_flight(cache_key):
            set_art_in_flight(cache_key, True)
            schedule_art(bg_resolve_art(r.artist, r.title, None, None, None))
        return PlayingNowResponse(
            is_playing=False,
            last_played=LastPlayedEntry(
                artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                cover_art_url=cached_art,
            ),
        )


@router.get("/last-played", response_model=PlayingNowResponse)
def get_last_played() -> PlayingNowResponse:
    """Return the most recent listen from the local DB with no LB network call."""
    rows = repo.get_recent_listens(limit=1)
    if not rows:
        return PlayingNowResponse(is_playing=False)
    r = rows[0]
    return PlayingNowResponse(
        is_playing=False,
        last_played=LastPlayedEntry(artist=r.artist, title=r.title, unix_ts=r.unix_ts),
    )


@router.get("/playing-now/stream")
async def playing_now_stream() -> StreamingResponse:
    """SSE stream that pushes playing-now state every 15 s."""
    return StreamingResponse(
        pn_broadcaster.subscribe(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
