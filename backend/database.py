import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")
JSON_PATH = os.path.join(os.path.dirname(__file__), "merged_history.json")

def get_db_connection():
    """Establish and return an SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema and build indices."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create listens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist TEXT NOT NULL,
            title TEXT NOT NULL,
            unix_ts INTEGER NOT NULL,
            source TEXT NOT NULL
        )
    """)
    
    # Create indices for fast queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listens_unix_ts ON listens(unix_ts)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listens_artist ON listens(artist)")
    
    conn.commit()
    conn.close()

def bootstrap_db_from_json():
    """Bootstrap the SQLite database from merged_history.json if the database is empty."""
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if database is empty
    cursor.execute("SELECT COUNT(*) FROM listens")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"Database already contains {count:,} entries. Skipping bootstrap.")
        conn.close()
        return False

    if not os.path.exists(JSON_PATH):
        print(f"merged_history.json not found at '{JSON_PATH}'. Skipping bootstrap.")
        conn.close()
        return False
        
    print(f"Bootstrapping database from {JSON_PATH}...")
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
            
        # Bulk insert
        cursor.executemany(
            "INSERT INTO listens (artist, title, unix_ts, source) VALUES (?, ?, ?, ?)",
            [(item["artist"], item["title"], item["unix_ts"], item.get("source", "unknown")) for item in history]
        )
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM listens")
        new_count = cursor.fetchone()[0]
        print(f"Successfully bootstrapped SQLite database with {new_count:,} records.")
        conn.close()
        return True
    except Exception as e:
        print(f"Error bootstrapping database: {e}")
        conn.close()
        return False

# ── Query Helpers ──────────────────────────────────────────────────────────────

def get_stats_summary() -> dict[str, Any]:
    """Calculate overall statistics from the scrobble database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total count
    cursor.execute("SELECT COUNT(*) FROM listens")
    total_listens = cursor.fetchone()[0]
    
    if total_listens == 0:
        conn.close()
        return {
            "total_listens": 0, "unique_artists": 0, "unique_tracks": 0,
            "days_active": 0, "avg_per_day": 0, "top_source": "None"
        }
        
    # Unique artists
    cursor.execute("SELECT COUNT(DISTINCT artist) FROM listens")
    unique_artists = cursor.fetchone()[0]
    
    # Unique tracks
    cursor.execute("SELECT COUNT(DISTINCT artist || ' - ' || title) FROM listens")
    unique_tracks = cursor.fetchone()[0]
    
    # Days active
    cursor.execute("SELECT COUNT(DISTINCT date(unix_ts, 'unixepoch', 'localtime')) FROM listens")
    days_active = cursor.fetchone()[0]
    
    # Top source
    cursor.execute("SELECT source, COUNT(*) as cnt FROM listens GROUP BY source ORDER BY cnt DESC LIMIT 1")
    source_row = cursor.fetchone()
    top_source = source_row["source"] if source_row else "unknown"
    
    # Average per day
    avg_per_day = round(total_listens / days_active, 1) if days_active > 0 else 0
    
    conn.close()
    return {
        "total_listens": total_listens,
        "unique_artists": unique_artists,
        "unique_tracks": unique_tracks,
        "days_active": days_active,
        "avg_per_day": avg_per_day,
        "top_source": top_source
    }

def get_time_range_clause(time_range_days: str) -> tuple[str, list[Any]]:
    """Generate SQL WHERE subclause and parameters for a day-based time range."""
    if not time_range_days or time_range_days == "all":
        return "", []
    try:
        days = int(time_range_days)
        # Calculate cut-off timestamp
        cutoff = int(datetime.now(timezone.utc).timestamp()) - (days * 86400)
        return "WHERE unix_ts >= ?", [cutoff]
    except ValueError:
        return "", []

def get_top_artists(time_range: str = "all", limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve top artists for a given time range."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    where_clause, params = get_time_range_clause(time_range)
    params.append(limit)
    
    query = f"""
        SELECT artist, COUNT(*) as play_count 
        FROM listens 
        {where_clause} 
        GROUP BY artist 
        ORDER BY play_count DESC 
        LIMIT ?
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [{"artist": r["artist"], "play_count": r["play_count"]} for r in rows]

def get_top_tracks(time_range: str = "all", limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve top tracks for a given time range."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    where_clause, params = get_time_range_clause(time_range)
    params.append(limit)
    
    query = f"""
        SELECT artist, title, COUNT(*) as play_count 
        FROM listens 
        {where_clause} 
        GROUP BY artist, title 
        ORDER BY play_count DESC 
        LIMIT ?
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [{"artist": r["artist"], "title": r["title"], "play_count": r["play_count"]} for r in rows]

def get_heatmap_data(year: int | str | None = None) -> dict[str, int]:
    """Retrieve counts of scrobbles grouped by date (YYYY-MM-DD) for a given year."""
    if not year:
        year = str(datetime.now().year)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date(unix_ts, 'unixepoch', 'localtime') as day, COUNT(*) as cnt 
        FROM listens 
        WHERE strftime('%Y', unix_ts, 'unixepoch', 'localtime') = ? 
        GROUP BY day
    """, [str(year)])
    rows = cursor.fetchall()
    conn.close()
    return {r["day"]: r["cnt"] for r in rows if r["day"]}

def get_hourly_trends() -> dict[str, int]:
    """Retrieve play counts grouped by hour of the day (00-23) in local time."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT strftime('%H', unix_ts, 'unixepoch', 'localtime') as hour, COUNT(*) as cnt 
        FROM listens 
        GROUP BY hour 
        ORDER BY hour ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # Initialize all 24 hours
    trends = {f"{h:02d}": 0 for h in range(24)}
    for r in rows:
        if r["hour"]:
            trends[r["hour"]] = r["cnt"]
    return trends

def get_monthly_trends() -> list[dict[str, Any]]:
    """Retrieve play counts grouped by month (YYYY-MM) in local time."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT strftime('%Y-%m', unix_ts, 'unixepoch', 'localtime') as month, COUNT(*) as cnt 
        FROM listens 
        GROUP BY month 
        ORDER BY month ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"month": r["month"], "count": r["cnt"]} for r in rows if r["month"]]

def get_streak_stats() -> dict[str, int]:
    """Calculate the current active streak and all-time longest consecutive listening streak (in days)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all distinct active dates sorted
    cursor.execute("""
        SELECT DISTINCT date(unix_ts, 'unixepoch', 'localtime') as day 
        FROM listens 
        ORDER BY day ASC
    """)
    days = [datetime.strptime(r["day"], "%Y-%m-%d").date() for r in cursor.fetchall() if r["day"]]
    conn.close()
    
    if not days:
        return {"current_streak": 0, "longest_streak": 0}
        
    longest = 0
    current = 0
    
    # Calculate streak
    last_date = None
    streak_list = []
    temp_streak = 0
    
    for d in days:
        if last_date is None:
            temp_streak = 1
        elif (d - last_date).days == 1:
            temp_streak += 1
        elif (d - last_date).days > 1:
            streak_list.append(temp_streak)
            temp_streak = 1
        last_date = d
        
    if temp_streak > 0:
        streak_list.append(temp_streak)
        
    longest = max(streak_list) if streak_list else 0
    
    # Current active streak check (is latest active day today or yesterday?)
    today = datetime.now().date()
    current_streak = 0
    if days:
        latest_active_day = days[-1]
        days_diff = (today - latest_active_day).days
        if days_diff <= 1:
            # Trailing consecutive days
            current_run = 0
            check_date = latest_active_day
            idx = len(days) - 1
            while idx >= 0:
                if days[idx] == check_date:
                    current_run += 1
                    check_date = check_date - timedelta(days=1)
                    idx -= 1
                else:
                    break
            current_streak = current_run
            
    return {
        "current_streak": current_streak,
        "longest_streak": max(longest, current_streak)
    }

def get_wrapped_data(year: int | None, quarter: str | None = None, month: str | None = None, decade: str | None = None) -> dict[str, Any]:
    """
    Retrieve highly detailed spotify-wrapped style metrics for custom periods.
    Supports years, quarters (Q1-Q4), specific months (M1-M12), and decades (10s, 20s).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    where_clauses: list[str] = []
    params: list[Any] = []
    
    # 1. Filter by year or decade
    if decade:
        if decade == "10s":
            where_clauses.append("unix_ts >= ? AND unix_ts <= ?")
            # 2010-01-01 00:00:00 to 2019-12-31 23:59:59 UTC
            params.extend([1262304000, 1577836799])
        elif decade == "20s":
            where_clauses.append("unix_ts >= ? AND unix_ts <= ?")
            # 2020-01-01 00:00:00 to 2029-12-31 23:59:59 UTC
            params.extend([1577836800, 1893455999])
    elif year is not None:
        where_clauses.append("strftime('%Y', unix_ts, 'unixepoch', 'localtime') = ?")
        params.append(str(year))
        
    # 2. Filter by quarter
    if quarter:
        # quarters Q1: 01-03, Q2: 04-06, Q3: 07-09, Q4: 10-12
        if quarter == "Q1":
            where_clauses.append("strftime('%m', unix_ts, 'unixepoch', 'localtime') IN ('01', '02', '03')")
        elif quarter == "Q2":
            where_clauses.append("strftime('%m', unix_ts, 'unixepoch', 'localtime') IN ('04', '05', '06')")
        elif quarter == "Q3":
            where_clauses.append("strftime('%m', unix_ts, 'unixepoch', 'localtime') IN ('07', '08', '09')")
        elif quarter == "Q4":
            where_clauses.append("strftime('%m', unix_ts, 'unixepoch', 'localtime') IN ('10', '11', '12')")
            
    # 3. Filter by month
    if month:
        # expect month format like '01' to '12' or 'M1' to 'M12'
        m_str = month.replace("M", "").zfill(2)
        where_clauses.append("strftime('%m', unix_ts, 'unixepoch', 'localtime') = ?")
        params.append(m_str)
        
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # ── Queries ──
    # A. Total plays
    cursor.execute(f"SELECT COUNT(*) FROM listens {where_sql}", params)
    total_plays = cursor.fetchone()[0]
    
    if total_plays == 0:
        conn.close()
        return {
            "total_plays": 0, "top_artist": None, "top_track": None,
            "peak_day": None, "minutes_listened": 0
        }
        
    # B. Top Artist
    cursor.execute(f"""
        SELECT artist, COUNT(*) as cnt 
        FROM listens 
        {where_sql} 
        GROUP BY artist 
        ORDER BY cnt DESC 
        LIMIT 1
    """, params)
    artist_row = cursor.fetchone()
    top_artist = {"name": artist_row["artist"], "plays": artist_row["cnt"]} if artist_row else None
    
    # C. Top Track
    cursor.execute(f"""
        SELECT artist, title, COUNT(*) as cnt 
        FROM listens 
        {where_sql} 
        GROUP BY artist, title 
        ORDER BY cnt DESC 
        LIMIT 1
    """, params)
    track_row = cursor.fetchone()
    top_track = {"artist": track_row["artist"], "title": track_row["title"], "plays": track_row["cnt"]} if track_row else None
    
    # D. Peak Listening Day
    cursor.execute(f"""
        SELECT date(unix_ts, 'unixepoch', 'localtime') as day, COUNT(*) as cnt 
        FROM listens 
        {where_sql} 
        GROUP BY day 
        ORDER BY cnt DESC 
        LIMIT 1
    """, params)
    day_row = cursor.fetchone()
    peak_day = {"date": day_row["day"], "plays": day_row["cnt"]} if day_row else None
    
    # E. Minutes Listened Estimate (industry average 3.5 minutes per play)
    minutes_listened = round(total_plays * 3.5)
    
    conn.close()
    return {
        "total_plays": total_plays,
        "top_artist": top_artist,
        "top_track": top_track,
        "peak_day": peak_day,
        "minutes_listened": minutes_listened
    }

def deduplicate_listens() -> int:
    """
    Remove duplicate listens where the same artist and title are scrobbled
    within 60 seconds of each other. Keeps the entry with the lower ID.
    Returns the number of deleted duplicate rows.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM listens 
        WHERE id IN (
            SELECT b.id 
            FROM listens a 
            JOIN listens b ON a.artist = b.artist 
                          AND a.title = b.title 
                          AND a.id < b.id 
                          AND abs(a.unix_ts - b.unix_ts) <= 60
        )
    """)
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count
