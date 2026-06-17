import csv
import io
import json
import logging
import os

from fastapi import APIRouter, BackgroundTasks, Header, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Any, List, Literal, Optional, Dict

logger = logging.getLogger(__name__)

import app.repository as repo
import app.sync as sync_worker
import httpx
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
)

router = APIRouter()

@router.get("/stats", response_model=StatsSummaryResponse)
def read_stats() -> Any:
    """Retrieve high-level listening history metrics."""
    return repo.get_stats_summary()
@router.get("/top-artists", response_model=TopArtistsResponse)
def read_top_artists(
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(15, ge=1, le=100, description="Max results to return"),
    search: Optional[str] = Query(None, description="Filter by artist name (case-insensitive substring)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size (overrides limit if set)"),
) -> Any:
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
) -> Any:
    """Retrieve top tracks for a specified time range."""
    actual_limit = page_size if page_size is not None else limit
    clean_search = search.strip() if search else None
    if clean_search == "":
        clean_search = None
    return repo.get_top_tracks(time_range=range_param, limit=actual_limit, page=page, search=clean_search)

@router.get("/heatmap", response_model=Dict[str, int])
def read_heatmap(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="The calendar year to display"),
) -> Any:
    """Retrieve daily play counts for a calendar heatmap visualization."""
    return repo.get_heatmap_data(year=year)

@router.get("/trends/hourly", response_model=Dict[str, int])
def read_hourly_trends() -> Any:
    """Retrieve play counts grouped by the hour of the day."""
    return repo.get_hourly_trends()

@router.get("/trends/punchcard", response_model=Dict[str, int])
def read_punchcard() -> Any:
    """Retrieve play counts grouped by day-of-week and hour (keys: '{dow}_{HH}', dow 0=Sun)."""
    return repo.get_punchcard_data()

@router.get("/trends/monthly", response_model=List[MonthlyTrendInfo])
def read_monthly_trends() -> Any:
    """Retrieve play counts grouped by month (chronological)."""
    return repo.get_monthly_trends()

@router.get("/trends/streak", response_model=StreakStatsResponse)
def read_streak() -> Any:
    """Retrieve active and historical daily listening streaks."""
    return repo.get_streak_stats()

@router.get("/wrapped", response_model=WrappedDataResponse)
def read_wrapped(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filter by year (e.g. 2025)"),
    quarter: Optional[Literal["Q1", "Q2", "Q3", "Q4"]] = Query(None, description="Filter by quarter: Q1, Q2, Q3, Q4"),
    month: Optional[Literal["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"]] = Query(None, description="Filter by month: M1 to M12"),
) -> Any:
    """Retrieve aggregated review stats for custom time intervals (Spotify Wrapped style)."""
    if not year:
        raise HTTPException(
            status_code=400,
            detail="You must specify a 'year' parameter.",
        )
    return repo.get_wrapped_data(year=year, quarter=quarter, month=month)

@router.get("/recent", response_model=List[ListenEntry])
def read_recent(
    limit: int = Query(50, ge=1, le=100, description="Max results per page (1–100)"),
    before_ts: Optional[int] = Query(None, description="Cursor: unix_ts of the last item from the previous page"),
    before_id: Optional[int] = Query(None, description="Cursor: id of the last item from the previous page"),
    anchor_date: Optional[str] = Query(None, description="Anchor date: seek to first listen on or before YYYY-MM-DD"),
) -> Any:
    """Retrieve recent listens in reverse-chronological order with cursor-based pagination."""
    return repo.get_recent_listens(limit=limit, before_ts=before_ts, before_id=before_id, anchor_date=anchor_date)

@router.get("/track-stats", response_model=TrackStatsResponse)
def read_track_stats(
    artist: str = Query(..., description="Artist name"),
    title: str = Query(..., description="Track title"),
    album: Optional[str] = Query(None, description="Optional album name to scope the count"),
) -> Any:
    """Retrieve all-time play count (and duration when available) for a specific track."""
    album_val = album.strip() if album and album.strip() else None
    play_count, duration = repo.get_track_stats(artist=artist, title=title, album=album_val)
    return {"play_count": play_count, "duration_secs": duration}

# Per-process cache so we only pay the MB/CAA lookup cost once per track per session.
# Only successful lookups are stored; failed attempts are counted separately so transient
# failures (MB timeouts, rate limits) don't permanently suppress art for the session.
_cover_art_cache: dict[tuple[str, str], str] = {}
_cover_art_attempts: dict[tuple[str, str], int] = {}
_MAX_ART_ATTEMPTS = 3

_UA = "the-record-dashboard/1.0 (https://github.com/philipreese/the-record)"


async def _get_caa_direct_url(client: httpx.AsyncClient, release_mbid: str) -> Optional[str]:
    """Resolve a direct archive.org image URL from Cover Art Archive (avoids the redirect)."""
    try:
        r = await client.get(
            f"https://coverartarchive.org/release/{release_mbid}",
            headers={"User-Agent": _UA},
            timeout=httpx.Timeout(4.0),
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
            timeout=httpx.Timeout(4.0),
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


async def _recording_to_release_mbid(client: httpx.AsyncClient, recording_mbid: str) -> Optional[str]:
    """Look up the best release MBID for a recording via MusicBrainz."""
    try:
        r = await client.get(
            f"https://musicbrainz.org/ws/2/recording/{recording_mbid}",
            params={"inc": "releases", "fmt": "json"},
            headers={"User-Agent": _UA},
            timeout=httpx.Timeout(3.0),
        )
        if r.status_code == 200:
            releases = r.json().get("releases", [])
            if releases:
                return releases[0]["id"]
    except Exception:
        logger.debug("MB recording-to-release lookup failed for recording_mbid=%s", recording_mbid, exc_info=True)
    return None


async def _search_cover_art_by_text(
    client: httpx.AsyncClient, artist: str, title: str
) -> Optional[str]:
    """Last-resort cover art lookup via MB text search when no MBID is in the LB response."""
    try:
        r = await client.get(
            "https://musicbrainz.org/ws/2/recording",
            params={
                "query": f'recording:"{title}" AND artistname:"{artist}"',
                "fmt": "json",
                "limit": "5",
            },
            headers={"User-Agent": _UA},
            timeout=httpx.Timeout(8.0),
        )
        if r.status_code != 200:
            logger.warning("MB text-search returned %d for %r / %r", r.status_code, artist, title)
            return None
        recordings = r.json().get("recordings", [])
        if not recordings:
            logger.warning("MB text-search found no recordings for %r / %r", artist, title)
            return None
        for recording in recordings:
            for release in recording.get("releases", []):
                url = await _get_caa_direct_url(client, release["id"])
                if url:
                    return url
        logger.warning("MB text-search found recordings for %r / %r but no CAA art in any release", artist, title)
    except Exception:
        logger.warning("MB text-search cover art lookup failed for %r / %r", artist, title, exc_info=True)
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
    """Resolve cover art URL with caching. Only caches successes; retries failures up to _MAX_ART_ATTEMPTS."""
    cache_key = _art_key(artist, title)
    if cache_key in _cover_art_cache:
        return _cover_art_cache[cache_key]
    attempts = _cover_art_attempts.get(cache_key, 0)
    if attempts >= _MAX_ART_ATTEMPTS:
        logger.debug("Cover art suppressed for %r / %r after %d failed attempts", artist, title, attempts)
        return None

    _cover_art_attempts[cache_key] = attempts + 1

    # Tier 1: release MBID (most specific)
    mbid = release_mbid
    if not mbid and recording_mbid:
        mbid = await _recording_to_release_mbid(client, recording_mbid)
    url: Optional[str] = None
    if mbid:
        url = await _get_caa_direct_url(client, mbid)
    # Tier 2: release group MBID (wider coverage in CAA)
    if not url and release_group_mbid:
        url = await _get_caa_release_group_url(client, release_group_mbid)
    # Tier 3: text search fallback
    if not url:
        url = await _search_cover_art_by_text(client, artist, title)

    if url:
        _cover_art_cache[cache_key] = url
    else:
        logger.warning(
            "Cover art resolution failed for %r / %r (attempt %d/%d); release_mbid=%s recording_mbid=%s",
            artist, title, attempts + 1, _MAX_ART_ATTEMPTS, release_mbid, recording_mbid,
        )
    return url


@router.get("/playing-now", response_model=PlayingNowResponse)
async def get_playing_now() -> Any:
    """Fetch the currently playing track from ListenBrainz, or the most recent listen if nothing is playing."""
    from app.sync import LISTENBRAINZ_USERNAME, LISTENBRAINZ_TOKEN

    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        rows = repo.get_recent_listens(limit=1)
        if not rows:
            return PlayingNowResponse(is_playing=False)
        r = rows[0]
        return PlayingNowResponse(
            is_playing=False,
            last_played=LastPlayedEntry(artist=r["artist"], title=r["title"], unix_ts=r["unix_ts"]),
        )

    lb_url = f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/playing-now"
    lb_headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "User-Agent": _UA,
    }
    try:

        from app.lb_client import get_lb_client
        client = get_lb_client()
        res = await client.get(lb_url, headers=lb_headers, timeout=httpx.Timeout(15.0))
        res.raise_for_status()

        listens = res.json().get("payload", {}).get("listens", [])
        if not listens:
            # Nothing playing — get the most recent DB listen, then fetch its MBIDs from
            # LB's listens endpoint so we can do a proper CAA lookup instead of text search.
            rows = repo.get_recent_listens(limit=1)
            if not rows:
                return PlayingNowResponse(is_playing=False)
            r = rows[0]
            lp_release_mbid: Optional[str] = None
            lp_recording_mbid: Optional[str] = None
            lp_release_group_mbid: Optional[str] = None
            try:
                lp_res = await client.get(
                    f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/listens",
                    params={"count": "1"},
                    headers=lb_headers,
                    timeout=httpx.Timeout(3.0),
                )
                if lp_res.status_code == 200:
                    lp_listens = lp_res.json().get("payload", {}).get("listens", [])
                    if lp_listens:
                        lp_mm = lp_listens[0].get("track_metadata", {}).get("mbid_mapping", {})
                        lp_release_mbid = lp_mm.get("caa_release_mbid") or lp_mm.get("release_mbid")
                        lp_recording_mbid = lp_mm.get("recording_mbid")
                        lp_release_group_mbid = lp_mm.get("release_group_mbid")
            except Exception:
                logger.debug("LB MBID enrichment fetch failed for last-played", exc_info=True)
            art = await _resolve_cover_art(
                client, r["artist"], r["title"],
                lp_release_mbid, lp_recording_mbid, lp_release_group_mbid
            )
            return PlayingNowResponse(
                is_playing=False,
                last_played=LastPlayedEntry(
                    artist=r["artist"], title=r["title"], unix_ts=r["unix_ts"], cover_art_url=art
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
            cover_art_url = await _resolve_cover_art(
                client, artist, title, release_mbid, recording_mbid, release_group_mbid
            )

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
        cached_art = _cover_art_cache.get(_art_key(r["artist"], r["title"]))
        return PlayingNowResponse(
            is_playing=False,
            last_played=LastPlayedEntry(
                artist=r["artist"], title=r["title"], unix_ts=r["unix_ts"],
                cover_art_url=cached_art,
            ),
        )

@router.get("/last-played", response_model=PlayingNowResponse)
def get_last_played() -> Any:
    """Return the most recent listen from the local DB with no LB network call — fast cold-start pre-population."""
    rows = repo.get_recent_listens(limit=1)
    if not rows:
        return PlayingNowResponse(is_playing=False)
    r = rows[0]
    return PlayingNowResponse(
        is_playing=False,
        last_played=LastPlayedEntry(artist=r["artist"], title=r["title"], unix_ts=r["unix_ts"]),
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
) -> Any:
    """
    Kick off a background sync with ListenBrainz and return immediately.
    Poll GET /api/sync/status for progress and results.
    """
    sync_token = os.getenv("SYNC_TOKEN")
    if not sync_token:
        raise HTTPException(status_code=503, detail="Sync endpoint is not configured.")
    if x_sync_token != sync_token:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Sync-Token.")

    async with sync_worker._sync_lock:
        if sync_worker._sync_state.running:
            return {
                "status": "already_running",
                "message": "A sync is already in progress. Poll /api/sync/status for updates.",
            }
        s = sync_worker._sync_state
        s.running = True
        s.mode = mode
        s.batches_fetched = 0
        s.synced_count = 0
        s.deleted_count = 0
        s.lb_total = 0
        s.local_total = 0
        s.error = None
        s.finished = False

    if mode == "mirror":
        background_tasks.add_task(sync_worker._run_mirror)
    else:
        background_tasks.add_task(sync_worker._run_sync, mode)
    return {"status": "started", "mode": mode}

@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status() -> Any:
    """Return the current state of the background sync job."""
    s = sync_worker._sync_state
    return {
        "running": s.running,
        "finished": s.finished,
        "mode": s.mode,
        "batches_fetched": s.batches_fetched,
        "synced_count": s.synced_count,
        "deleted_count": s.deleted_count,
        "lb_total": s.lb_total,
        "local_total": s.local_total,
        "error": s.error,
    }

@router.get("/on-this-day", response_model=List[OnThisDayGroup])
def read_on_this_day() -> Any:
    """Retrieve listens for today's calendar date grouped by prior year."""
    from datetime import datetime
    today = datetime.now()
    return repo.get_on_this_day(today.month, today.day)


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

