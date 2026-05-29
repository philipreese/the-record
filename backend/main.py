import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, Any, AsyncGenerator

from fastapi import BackgroundTasks, FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

# Import database module
from database import (
    bootstrap_db_from_json,
    get_stats_summary,
    get_top_artists,
    get_top_tracks,
    get_heatmap_data,
    get_hourly_trends,
    get_monthly_trends,
    get_streak_stats,
    get_wrapped_data,
)

import sync

load_dotenv(dotenv_path=".env")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ensure database schema exists and bootstrap initial data on startup."""
    bootstrap_db_from_json()
    yield


app = FastAPI(title="The Record API", version="1.0.0", lifespan=lifespan)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------

@app.get("/api/stats")
def read_stats() -> dict[str, Any]:
    """Retrieve high-level listening history metrics."""
    return get_stats_summary()


@app.get("/api/top-artists")
def read_top_artists(
    range_param: str = Query("all", alias="range", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(10, description="Max results to return"),
) -> list[dict[str, Any]]:
    """Retrieve top artists for a specified time range."""
    return get_top_artists(time_range=range_param, limit=limit)


@app.get("/api/top-tracks")
def read_top_tracks(
    range_param: str = Query("all", alias="range", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(10, description="Max results to return"),
) -> list[dict[str, Any]]:
    """Retrieve top tracks for a specified time range."""
    return get_top_tracks(time_range=range_param, limit=limit)


@app.get("/api/heatmap")
def read_heatmap(
    year: Optional[int] = Query(None, description="The calendar year to display"),
) -> dict[str, int]:
    """Retrieve daily play counts for a calendar heatmap visualization."""
    return get_heatmap_data(year=year)


@app.get("/api/trends/hourly")
def read_hourly_trends() -> dict[str, int]:
    """Retrieve play counts grouped by the hour of the day."""
    return get_hourly_trends()


@app.get("/api/trends/monthly")
def read_monthly_trends() -> list[dict[str, Any]]:
    """Retrieve play counts grouped by month (chronological)."""
    return get_monthly_trends()


@app.get("/api/trends/streak")
def read_streak() -> dict[str, int]:
    """Retrieve active and historical daily listening streaks."""
    return get_streak_stats()


@app.get("/api/wrapped")
def read_wrapped(
    year: Optional[int] = Query(None, description="Filter by year (e.g. 2025)"),
    quarter: Optional[str] = Query(None, description="Filter by quarter: Q1, Q2, Q3, Q4"),
    month: Optional[str] = Query(None, description="Filter by month: M1 to M12"),
) -> dict[str, Any]:
    """Retrieve aggregated review stats for custom time intervals (Spotify Wrapped style)."""
    if not year:
        raise HTTPException(
            status_code=400,
            detail="You must specify a 'year' parameter.",
        )
    return get_wrapped_data(year=year, quarter=quarter, month=month)


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------

@app.post("/api/sync")
async def start_sync(
    background_tasks: BackgroundTasks,
    mode: str = Query("normal", description="Sync mode: 'normal' or 'full'"),
) -> dict[str, Any]:
    """
    Kick off a background sync with ListenBrainz and return immediately.
    Poll GET /api/sync/status for progress and results.
    """
    if sync._sync_state.running:
        return {
            "status": "already_running",
            "message": "A sync is already in progress. Poll /api/sync/status for updates.",
        }

    # Reset state for this run
    sync._sync_state = sync.SyncState(running=True, mode=mode)
    background_tasks.add_task(sync._run_sync, mode)

    return {"status": "started", "mode": mode}


@app.get("/api/sync/status")
def get_sync_status() -> dict[str, Any]:
    """Return the current state of the background sync job."""
    s = sync._sync_state
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
