from fastapi import APIRouter, BackgroundTasks, Query, HTTPException
from typing import Any, List, Literal, Optional, Dict

import app.repository as repo
import app.sync as sync_worker
from app.schemas import (
    StatsSummaryResponse,
    ArtistInfo,
    TrackInfo,
    MonthlyTrendInfo,
    StreakStatsResponse,
    WrappedDataResponse,
    SyncStartResponse,
    SyncStatusResponse
)

router = APIRouter()

@router.get("/stats", response_model=StatsSummaryResponse)
def read_stats() -> Any:
    """Retrieve high-level listening history metrics."""
    return repo.get_stats_summary()

@router.get("/top-artists", response_model=List[ArtistInfo])
def read_top_artists(
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(15, ge=1, le=100, description="Max results to return"),
) -> Any:
    """Retrieve top artists for a specified time range."""
    return repo.get_top_artists(time_range=range_param, limit=limit)

@router.get("/top-tracks", response_model=List[TrackInfo])
def read_top_tracks(
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(15, ge=1, le=100, description="Max results to return"),
) -> Any:
    """Retrieve top tracks for a specified time range."""
    return repo.get_top_tracks(time_range=range_param, limit=limit)

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

@router.post("/sync", response_model=SyncStartResponse)
async def start_sync(
    background_tasks: BackgroundTasks,
    mode: Literal["normal", "full"] = Query("normal", description="Sync mode: 'normal' or 'full'"),
) -> Any:
    """
    Kick off a background sync with ListenBrainz and return immediately.
    Poll GET /api/sync/status for progress and results.
    """
    if sync_worker._sync_state.running:
        return {
            "status": "already_running",
            "message": "A sync is already in progress. Poll /api/sync/status for updates.",
        }

    # Reset state for this run
    sync_worker._sync_state = sync_worker.SyncState(running=True, mode=mode)
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
        "lb_total": s.lb_total,
        "local_total": s.local_total,
        "error": s.error,
    }
