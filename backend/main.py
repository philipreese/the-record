import os
import sys
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

# Import database module
from database import (
    bootstrap_db_from_json,
    get_db_connection,
    get_stats_summary,
    get_top_artists,
    get_top_tracks,
    get_heatmap_data,
    get_hourly_trends,
    get_monthly_trends,
    get_streak_stats,
    get_wrapped_data
)

load_dotenv(dotenv_path=".env")

LISTENBRAINZ_USERNAME = os.getenv("LISTENBRAINZ_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

@asynccontextmanager
async def lifespan(app: FastAPI):
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

@app.get("/api/stats")
def read_stats():
    """Retrieve high-level listening history metrics."""
    return get_stats_summary()

@app.get("/api/top-artists")
def read_top_artists(
    range: str = Query("all", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(10, description="Max results to return")
):
    """Retrieve top artists for a specified time range."""
    return get_top_artists(time_range=range, limit=limit)

@app.get("/api/top-tracks")
def read_top_tracks(
    range: str = Query("all", description="Time range in days: 30, 90, 365, or 'all'"),
    limit: int = Query(10, description="Max results to return")
):
    """Retrieve top tracks for a specified time range."""
    return get_top_tracks(time_range=range, limit=limit)

@app.get("/api/heatmap")
def read_heatmap(
    year: int = Query(None, description="The calendar year to display")
):
    """Retrieve daily play counts for a calendar heatmap visualization."""
    return get_heatmap_data(year=year)

@app.get("/api/trends/hourly")
def read_hourly_trends():
    """Retrieve play counts grouped by the hour of the day."""
    return get_hourly_trends()

@app.get("/api/trends/monthly")
def read_monthly_trends():
    """Retrieve play counts grouped by month (chronological)."""
    return get_monthly_trends()

@app.get("/api/trends/streak")
def read_streak():
    """Retrieve active and historical daily listening streaks."""
    return get_streak_stats()

@app.get("/api/wrapped")
def read_wrapped(
    year: int = Query(None, description="Filter by year (e.g. 2025)"),
    quarter: str = Query(None, description="Filter by quarter: Q1, Q2, Q3, Q4"),
    month: str = Query(None, description="Filter by month: M1 to M12"),
    decade: str = Query(None, description="Filter by decade: 10s, 20s")
):
    """Retrieve aggregated review stats for custom time intervals (Spotify Wrapped style)."""
    if not year and not decade:
        raise HTTPException(
            status_code=400,
            detail="You must specify either a 'year' or a 'decade' parameter."
        )
    return get_wrapped_data(year=year, quarter=quarter, month=month, decade=decade)

@app.post("/api/sync")
async def sync_listens(mode: str = Query("normal", description="Sync mode: 'normal' or 'full'")):
    """
    Synchronize local database with the ListenBrainz API.
    Fetches plays submitted since our local maximum timestamp, or performs a backfill
    if local count differs from ListenBrainz.
    """
    if not LISTENBRAINZ_USERNAME or not LISTENBRAINZ_TOKEN:
        raise HTTPException(
            status_code=400,
            detail="Credentials missing. Please configure LISTENBRAINZ_USERNAME and LISTENBRAINZ_TOKEN in your .env file."
        )
        
    headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "User-Agent": "the-record-dashboard-sync/1.0"
    }

    # 1. Fetch total count from ListenBrainz
    lb_total_count = 0
    async with httpx.AsyncClient() as client:
        try:
            count_url = f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/listen-count"
            count_res = await client.get(count_url, headers=headers)
            count_res.raise_for_status()
            lb_total_count = count_res.json().get("payload", {}).get("count", 0)
        except Exception:
            # Fallback to 0 if the endpoint fails
            lb_total_count = 0

    # 2. Get local database count and latest timestamp
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM listens")
    local_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(unix_ts) FROM listens")
    max_ts_row = cursor.fetchone()
    latest_ts = max_ts_row[0] if max_ts_row and max_ts_row[0] is not None else 0
    
    # 3. Load all local keys to prevent duplicates
    cursor.execute("SELECT unix_ts, artist, title FROM listens")
    local_keys = {(row[0], row[1].lower(), row[2].lower()) for row in cursor.fetchall()}
    conn.close()
    
    # Determine if we need backfill
    backfill = (mode == "full") or (lb_total_count > local_count)
    missing_count = lb_total_count - local_count if lb_total_count > local_count else 0
    
    new_listens = []
    current_max_ts = None
    stop_sync = False
    
    # Use larger count for backfill to minimize API requests
    batch_size = 1000 if backfill else 100
    
    async with httpx.AsyncClient() as client:
        while not stop_sync:
            url = f"https://api.listenbrainz.org/1/user/{LISTENBRAINZ_USERNAME}/listens?count={batch_size}"
            if current_max_ts:
                url += f"&max_ts={current_max_ts}"
                
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 429:
                    reset_in = response.headers.get("X-RateLimit-Reset-In", "5")
                    raise HTTPException(
                        status_code=429,
                        detail=f"ListenBrainz API rate-limited. Retry in {reset_in} seconds."
                    )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"API error: {e}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Connection failure: {e}")
                
            payload = data.get("payload", {})
            listens = payload.get("listens", [])
            
            if not listens:
                break
                
            for listen in listens:
                ts = listen.get("listened_at")
                if ts is None:
                    continue
                    
                meta = listen.get("track_metadata", {})
                artist = meta.get("artist_name")
                title = meta.get("track_name")
                
                if artist and title:
                    key = (ts, artist.lower(), title.lower())
                    if key not in local_keys:
                        new_listens.append((artist, title, ts, "listenbrainz_sync"))
                        local_keys.add(key)
                        if missing_count > 0:
                            missing_count -= 1
                            if missing_count == 0 and backfill and mode != "full":
                                stop_sync = True
                                break
                    
                # If we're not in backfill mode, stop when we see an entry older than or equal to latest_ts
                if not backfill and ts <= latest_ts:
                    stop_sync = True
                    break
            
            if stop_sync:
                break
                
            if len(listens) == batch_size:
                current_max_ts = listens[-1].get("listened_at")
            else:
                break
                
    # Insert new scrobbles (in chronological order)
    if new_listens:
        new_listens.reverse()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO listens (artist, title, unix_ts, source) VALUES (?, ?, ?, ?)",
            new_listens
        )
        conn.commit()
        conn.close()
        
    return {
        "status": "success",
        "synced_count": len(new_listens),
        "latest_timestamp": latest_ts,
        "backfill_run": backfill
    }
