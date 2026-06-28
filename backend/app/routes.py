import asyncio
import csv
import hmac
import io
import json
import logging
import os
from collections import OrderedDict

from fastapi import APIRouter, BackgroundTasks, Header, Query, HTTPException, Path, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from typing import Any, List, Literal, Optional, Dict

logger = logging.getLogger(__name__)

import app.repository as repo
import app.sync as sync_worker
import httpx
from app.narrative import generate_narrative
from app.ws import manager as ws_manager
from app.playing_now_sse import broadcaster as pn_broadcaster
from app.schemas import (
    StatsSummaryResponse,
    ArtistInfo,
    ListenEntry,
    TrackInfo,
    MonthlyTrendInfo,
    StreakStatsResponse,
    WrappedDataResponse,
    SyncStartResponse,
    SyncStatusResponse,
    PlayingNowResponse,
    LastPlayedEntry,
    TrackStatsResponse,
    OnThisDayGroup,
    TopArtistsResponse,
    TopTracksResponse,
    TrackBatchRequestItem,
    TrackBatchResponseItem,
    WeeklyBreakdownItem,
    TopArtistTrendsResponse,
    ArtistTrendResponse,
    NarrativeResponse,
    ArtistStatsResponse,
    ArtistAnniversary,
    OnThisDayResponse,
)

router = APIRouter()

@router.get("/stats", response_model=StatsSummaryResponse)
def read_stats() -> StatsSummaryResponse:
    """Retrieve high-level listening history metrics."""
    return repo.get_stats_summary()
@router.get("/top-artists", response_model=TopArtistsResponse)
def read_top_artists(
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(15, ge=1, le=100, description="Max results to return"),
    search: Optional[str] = Query(None, description="Filter by artist name (case-insensitive substring)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size (overrides limit if set)"),
) -> TopArtistsResponse:
    """Retrieve top artists for a specified time range."""
    actual_limit = page_size if page_size is not None else limit
    clean_search = search.strip() if search else None
    if clean_search == "":
        clean_search = None
    return repo.get_top_artists(time_range=range_param, limit=actual_limit, page=page, search=clean_search)

@router.get("/top-tracks", response_model=TopTracksResponse)
def read_top_tracks(
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(15, ge=1, le=100, description="Max results to return"),
    search: Optional[str] = Query(None, description="Filter by track or artist name (case-insensitive substring)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size (overrides limit if set)"),
) -> TopTracksResponse:
    """Retrieve top tracks for a specified time range."""
    actual_limit = page_size if page_size is not None else limit
    clean_search = search.strip() if search else None
    if clean_search == "":
        clean_search = None
    return repo.get_top_tracks(time_range=range_param, limit=actual_limit, page=page, search=clean_search)

@router.get("/heatmap", response_model=Dict[str, int])
def read_heatmap(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="The calendar year to display"),
) -> dict[str, int]:
    """Retrieve daily play counts for a calendar heatmap visualization."""
    return repo.get_heatmap_data(year=year)

@router.get("/trends/hourly", response_model=Dict[str, int])
def read_hourly_trends() -> dict[str, int]:
    """Retrieve play counts grouped by the hour of the day."""
    return repo.get_hourly_trends()

@router.get("/trends/punchcard", response_model=Dict[str, int])
def read_punchcard() -> dict[str, int]:
    """Retrieve play counts grouped by day-of-week and hour (keys: '{dow}_{HH}', dow 0=Sun)."""
    return repo.get_punchcard_data()

@router.get("/trends/monthly", response_model=List[MonthlyTrendInfo])
def read_monthly_trends() -> list[MonthlyTrendInfo]:
    """Retrieve play counts grouped by month (chronological)."""
    return repo.get_monthly_trends()

@router.get("/trends/streak", response_model=StreakStatsResponse)
def read_streak() -> StreakStatsResponse:
    """Retrieve active and historical daily listening streaks."""
    return repo.get_streak_stats()

@router.get("/narrative", response_model=NarrativeResponse)
def read_narrative(
    seed: Optional[str] = Query(None, description="Optional seed for daily stable randomization"),
) -> NarrativeResponse:
    """Retrieve dynamic narrative strings for the UI."""
    stats = repo.get_stats_summary()
    streak = repo.get_streak_stats()
    return generate_narrative(stats, streak, seed)


@router.get("/wrapped", response_model=WrappedDataResponse)
def read_wrapped(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filter by year (e.g. 2025)"),
    quarter: Optional[Literal["Q1", "Q2", "Q3", "Q4"]] = Query(None, description="Filter by quarter: Q1, Q2, Q3, Q4"),
    month: Optional[Literal["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"]] = Query(None, description="Filter by month: M1 to M12"),
) -> WrappedDataResponse:
    """Retrieve aggregated review stats for custom time intervals (Spotify Wrapped style)."""
    if not year:
        raise HTTPException(
            status_code=400,
            detail="You must specify a 'year' parameter.",
        )
    return repo.get_wrapped_data(year=year, quarter=quarter, month=month)

@router.get("/recent", response_model=List[ListenEntry])
async def read_recent(
    limit: int = Query(50, ge=1, le=100, description="Max results per page (1–100)"),
    before_ts: Optional[int] = Query(None, description="Cursor: unix_ts of the last item from the previous page"),
    before_id: Optional[int] = Query(None, description="Cursor: id of the last item from the previous page"),
    anchor_date: Optional[str] = Query(None, description="Anchor date: seek to first listen on or before YYYY-MM-DD"),
) -> list[ListenEntry]:
    """Retrieve recent listens in reverse-chronological order with cursor-based pagination."""
    listens = await run_in_threadpool(
        repo.get_recent_listens, limit=limit, before_ts=before_ts,
        before_id=before_id, anchor_date=anchor_date,
    )
    _populate_cover_art(listens)
    return listens

@router.get("/track-stats", response_model=TrackStatsResponse)
def read_track_stats(
    artist: str = Query(..., description="Artist name"),
    title: str = Query(..., description="Track title"),
    album: Optional[str] = Query(None, description="Optional album name to scope the count"),
) -> TrackStatsResponse:
    """Retrieve all-time play count (and duration when available) for a specific track."""
    album_val = album.strip() if album and album.strip() else None
    play_count, duration = repo.get_track_stats(artist=artist, title=title, album=album_val)
    return TrackStatsResponse(play_count=play_count, duration_secs=duration)

# Upper bound on the batch endpoint: each pair expands into an OR/AND clause in the
# query, so an unbounded list would build a pathological statement. The UI only ever
# requests stats for the listens currently on screen, well under this cap.
_MAX_BATCH_TRACKS = 500


@router.post("/track-stats/batch", response_model=List[TrackBatchResponseItem])
def read_track_stats_batch(
    tracks: List[TrackBatchRequestItem]
) -> list[TrackBatchResponseItem]:
    """Retrieve all-time play count and first available non-null duration for a list of tracks."""
    if len(tracks) > _MAX_BATCH_TRACKS:
        raise HTTPException(
            status_code=422,
            detail=f"Too many tracks in one batch (max {_MAX_BATCH_TRACKS}).",
        )
    track_dicts = [{"artist": t.artist, "title": t.title} for t in tracks]
    return repo.get_track_stats_batch(track_dicts)


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


# Per-process cache so we only pay the MB/CAA lookup cost once per track per session.
# Both successful and failed lookups (after _MAX_ART_ATTEMPTS) are stored to prevent
# hitting rate limits and causing slow HTTP cascades on consecutive polls.
_ART_CACHE_MAX = 2048
_cover_art_cache: "OrderedDict[tuple[str, str], Optional[str]]" = _BoundedCache(_ART_CACHE_MAX)
_cover_art_attempts: "OrderedDict[tuple[str, str], int]" = _BoundedCache(_ART_CACHE_MAX)
_MAX_ART_ATTEMPTS = 3
# Tracks keys currently being resolved in background to prevent duplicate tasks.
_art_in_flight: set[tuple[str, str]] = set()
# One background iTunes request at a time with a post-request sleep keeps us
# well under Apple's undocumented rate limit (~20 req/min observed in practice).
_art_semaphore = asyncio.Semaphore(1)

_UA = "the-record-dashboard/1.0 (https://github.com/philipreese/the-record)"


async def _get_caa_direct_url(client: httpx.AsyncClient, release_mbid: str) -> Optional[str]:
    """Resolve a direct archive.org image URL from Cover Art Archive (avoids the redirect)."""
    try:
        r = await client.get(
            f"https://coverartarchive.org/release/{release_mbid}",
            headers={"User-Agent": _UA},
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
            headers={"User-Agent": _UA},
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


async def _search_cover_art_itunes(
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


def _art_key(artist: str, title: str) -> tuple[str, str]:
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
    cache_key = _art_key(artist, title)
    if cache_key in _cover_art_cache:
        return _cover_art_cache[cache_key]
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
        url = await _search_cover_art_itunes(client, artist, title)

    if url:
        _cover_art_cache[cache_key] = url
    else:
        logger.debug(
            "Cover art resolution failed for %r / %r (attempt %d/%d); release_mbid=%s recording_mbid=%s release_group_mbid=%s",
            artist, title, attempts + 1, _MAX_ART_ATTEMPTS, release_mbid, recording_mbid, release_group_mbid,
        )
        if attempts + 1 >= _MAX_ART_ATTEMPTS:
            _cover_art_cache[cache_key] = None
    return url


async def _bg_resolve_art(
    artist: str,
    title: str,
    release_mbid: Optional[str],
    recording_mbid: Optional[str],
    release_group_mbid: Optional[str],
) -> None:
    """Resolve cover art in the background and persist the result to the DB cache."""
    cache_key = _art_key(artist, title)
    try:
        async with _art_semaphore:
            async with httpx.AsyncClient(headers={"User-Agent": _UA}) as bg:
                await _resolve_cover_art(bg, artist, title, release_mbid, recording_mbid, release_group_mbid)
            if cache_key in _cover_art_cache:
                await run_in_threadpool(
                    repo.upsert_cover_art, cache_key[0], cache_key[1], _cover_art_cache.get(cache_key)
                )
            # Hold the semaphore through the sleep so concurrent tasks queue up
            # and we stay under iTunes' rate limit (~20 req/min).
            await asyncio.sleep(3.0)
    except Exception:
        logger.debug("Background cover art resolution failed for %r / %r", artist, title, exc_info=True)
    finally:
        _art_in_flight.discard(cache_key)



def _schedule_art(coro) -> None:
    """Schedule a background art task if the event loop is running."""
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        pass


def _populate_cover_art(listens: list) -> None:
    """Fill cover_art_url from in-process cache then DB for each listen."""
    mem_misses: list[tuple] = []
    for listen in listens:
        key = _art_key(listen.artist, listen.title)
        if key in _cover_art_cache:
            listen.cover_art_url = _cover_art_cache[key]
        else:
            mem_misses.append((listen, key))
    if mem_misses:
        db_hits = repo.get_cover_art_batch([k for _, k in mem_misses])
        for listen, key in mem_misses:
            if key in db_hits:
                _cover_art_cache[key] = db_hits[key]
                listen.cover_art_url = db_hits[key]


class _CoverArtItem(BaseModel):
    id: int
    artist: str
    title: str
    recording_mbid: Optional[str] = None


@router.post("/cover-art", response_model=Dict[str, Optional[str]])
async def get_cover_art(items: List[_CoverArtItem]) -> Dict[str, Optional[str]]:
    """Return cached cover art URLs and schedule background resolution for misses."""
    result: Dict[str, Optional[str]] = {}
    mem_misses: list[_CoverArtItem] = []
    for item in items[:100]:
        key = _art_key(item.artist, item.title)
        if key in _cover_art_cache:
            result[str(item.id)] = _cover_art_cache[key]
        else:
            mem_misses.append(item)

    if mem_misses:
        db_hits = await run_in_threadpool(
            repo.get_cover_art_batch, [_art_key(i.artist, i.title) for i in mem_misses]
        )
        for item in mem_misses:
            key = _art_key(item.artist, item.title)
            if key in db_hits:
                _cover_art_cache[key] = db_hits[key]
                result[str(item.id)] = db_hits[key]
            else:
                result[str(item.id)] = None
                if key not in _art_in_flight:
                    _art_in_flight.add(key)
                    _schedule_art(_bg_resolve_art(item.artist, item.title, None, item.recording_mbid, None))

    return result


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
        "User-Agent": _UA,
    }
    try:

        from app.lb_client import get_lb_client
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
            cache_key = _art_key(r.artist, r.title)
            if cache_key in _cover_art_cache:
                return PlayingNowResponse(
                    is_playing=False,
                    last_played=LastPlayedEntry(
                        artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                        cover_art_url=_cover_art_cache[cache_key],
                    ),
                )
            # Cache miss: resolve inline — iTunes answers in ~100ms so the added
            # latency is negligible compared to the LB API call above.
            async with httpx.AsyncClient(headers={"User-Agent": _UA}) as art_client:
                np_art = await _search_cover_art_itunes(art_client, r.artist, r.title)
            _cover_art_cache[cache_key] = np_art
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
            np_key = _art_key(artist, title)
            if np_key in _cover_art_cache:
                cover_art_url = _cover_art_cache[np_key]
            else:
                async with httpx.AsyncClient(headers={"User-Agent": _UA}) as art_client:
                    cover_art_url = await _search_cover_art_itunes(art_client, artist, title)
                _cover_art_cache[np_key] = cover_art_url
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
        cache_key = _art_key(r.artist, r.title)
        cached_art = _cover_art_cache.get(cache_key)
        if cache_key not in _cover_art_cache and cache_key not in _art_in_flight:
            _art_in_flight.add(cache_key)
            _schedule_art(_bg_resolve_art(r.artist, r.title, None, None, None))
        return PlayingNowResponse(
            is_playing=False,
            last_played=LastPlayedEntry(
                artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                cover_art_url=cached_art,
            ),
        )

@router.get("/last-played", response_model=PlayingNowResponse)
def get_last_played() -> PlayingNowResponse:
    """Return the most recent listen from the local DB with no LB network call — fast cold-start pre-population."""
    rows = repo.get_recent_listens(limit=1)
    if not rows:
        return PlayingNowResponse(is_playing=False)
    r = rows[0]
    return PlayingNowResponse(
        is_playing=False,
        last_played=LastPlayedEntry(artist=r.artist, title=r.title, unix_ts=r.unix_ts),
    )

@router.post("/sync", response_model=SyncStartResponse)
async def start_sync(
    background_tasks: BackgroundTasks,
    mode: Literal["normal", "mirror"] = Query(
        "normal",
        description=(
            "Sync mode. "
            "'normal': fast two-pass additive sync — pulls new scrobbles since last sync, then backfills any gaps. Safe to run daily. "
            "'mirror': fetches your complete ListenBrainz history, inserts any missing rows, and deletes any local rows not on LB. "
            "Treats LB as the authoritative source of truth. Takes ~15 minutes for large histories."
        ),
    ),
    x_sync_token: Optional[str] = Header(None),
) -> SyncStartResponse:
    """
    Kick off a background sync with ListenBrainz and return immediately.
    Poll GET /api/sync/status for progress and results.
    """
    sync_token = os.getenv("SYNC_TOKEN")
    if not sync_token:
        raise HTTPException(status_code=503, detail="Sync endpoint is not configured.")
    if not x_sync_token or not hmac.compare_digest(x_sync_token, sync_token):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Sync-Token.")

    async with sync_worker._sync_lock:
        if sync_worker._sync_state.running:
            return SyncStartResponse(
                status="already_running",
                message="A sync is already in progress. Poll /api/sync/status for updates.",
            )
        s = sync_worker._sync_state
        s.running = True
        s.mode = mode
        s.batches_fetched = 0
        s.synced_count = 0
        s.updated_count = 0
        s.deleted_count = 0
        s.lb_total = 0
        s.local_total = 0
        s.error = None
        s.finished = False

    if mode == "mirror":
        background_tasks.add_task(sync_worker._run_mirror)
    else:
        background_tasks.add_task(sync_worker._run_sync, mode)
    return SyncStartResponse(status="started", mode=mode)

@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    """Return the current state of the background sync job."""
    s = sync_worker._sync_state
    return SyncStatusResponse(
        running=s.running,
        finished=s.finished,
        mode=s.mode,
        batches_fetched=s.batches_fetched,
        synced_count=s.synced_count,
        updated_count=s.updated_count,
        deleted_count=s.deleted_count,
        lb_total=s.lb_total,
        local_total=s.local_total,
        error=s.error,
    )

@router.get("/on-this-day", response_model=OnThisDayResponse)
async def read_on_this_day() -> OnThisDayResponse:
    """Retrieve listens for today's calendar date grouped by prior year."""
    from datetime import datetime
    today = datetime.now()
    response = await run_in_threadpool(repo.get_on_this_day, today.month, today.day)
    for group in response.groups:
        _populate_cover_art(group.listens)
    return response


@router.get("/export")
def export_listens(
    format: Literal["csv", "json"] = Query("csv"),
    range: str = Query("all"),
) -> StreamingResponse:
    """Export listening history as CSV or JSON download."""
    rows = repo.get_export_data(range_days=range)

    if format == "json":
        content = json.dumps(rows, ensure_ascii=False, indent=2)
        filename = f"listening-history-{range}.json"
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    filename = f"listening-history-{range}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/day/{date_str}", response_model=List[ListenEntry])
def read_day_listens(
    date_str: str = Path(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Calendar date (YYYY-MM-DD) in local timezone"),
) -> list[ListenEntry]:
    """Retrieve all listens for a specific calendar date, in chronological order."""
    return repo.get_listens_by_day(date_str)


@router.get("/trends/monthly/{year}/{month}/weekly", response_model=List[WeeklyBreakdownItem])
def read_monthly_weekly_breakdown(
    year: int = Path(..., ge=2000, le=2100),
    month: int = Path(..., ge=1, le=12),
) -> list[WeeklyBreakdownItem]:
    """Retrieve play counts grouped by week-of-month for a given year and month."""
    return repo.get_weekly_breakdown(year, month)


@router.get("/top-artist-trends", response_model=TopArtistTrendsResponse)
def read_top_artist_trends(
    year: int = Query(..., ge=2000, le=2100, description="The calendar year to display"),
    limit: int = Query(5, ge=1, le=20, description="Max artists to return"),
) -> TopArtistTrendsResponse:
    """Retrieve top N artists with their monthly breakdowns for a specified year."""
    return repo.get_top_artist_trends(year=year, limit=limit)


@router.get("/artist-trend", response_model=ArtistTrendResponse)
def read_artist_trend(
    artist: str = Query(..., description="Artist name"),
    year: int = Query(..., ge=2000, le=2100, description="The calendar year to display"),
    limit: int = Query(5, ge=1, le=20, description="Max tracks to return"),
) -> ArtistTrendResponse:
    """Retrieve top N tracks of an artist with their monthly breakdowns for a specified year."""
    clean_artist = artist.strip()
    if not clean_artist:
        raise HTTPException(status_code=400, detail="Artist name cannot be empty.")
    return repo.get_artist_track_trends(artist=clean_artist, year=year, limit=limit)


@router.get("/artist/stats", response_model=ArtistStatsResponse)
def read_artist_stats(
    name: str = Query(..., description="Artist name"),
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range"),
) -> ArtistStatsResponse:
    """Retrieve comprehensive personal listening stats for a specific artist."""
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Artist name cannot be empty.")
    return repo.get_artist_stats(artist=clean_name, time_range=range_param)




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


@router.websocket("/ws/sync")
async def sync_ws(websocket: WebSocket) -> None:
    """WebSocket endpoint that pushes sync lifecycle events to connected clients."""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
