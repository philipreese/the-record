from datetime import datetime, date, timezone, timedelta
from typing import Any, List
import os
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, desc, distinct, text, tuple_
from app.db import get_engine, Listen
from app.db_helpers import IS_POSTGRES, get_date_expr, get_hour_expr, get_month_expr, get_month_num_expr, get_day_num_expr, get_year_expr, get_day_of_week_expr

def get_current_local_date() -> date:
    """Resolve the current calendar date in the configured TZ timezone, falling back to local system date."""
    tz_name = os.environ.get("TZ")
    if tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            pass
    return datetime.now().date()

def get_stats_summary() -> dict[str, Any]:
    """Calculate overall statistics from the scrobble database."""
    with get_engine().connect() as conn:
        # Total count
        total_listens = conn.execute(select(func.count(Listen.id))).scalar() or 0
        
        db_type = "PostgreSQL (Neon)" if IS_POSTGRES else "SQLite (Local)"
        
        if total_listens == 0:
            return {
                "total_listens": 0, "unique_artists": 0, "unique_tracks": 0,
                "days_active": 0, "avg_per_day": 0.0, "top_source": "None",
                "db_type": db_type
            }
            
        # Unique artists
        unique_artists = conn.execute(select(func.count(distinct(Listen.artist)))).scalar() or 0
        
        # Unique tracks
        unique_tracks = conn.execute(select(func.count(distinct(Listen.artist + " - " + Listen.title)))).scalar() or 0
        
        # Days active
        date_exp = get_date_expr(Listen.unix_ts)
        days_active = conn.execute(select(func.count(distinct(date_exp)))).scalar() or 0
        
        # Top source
        stmt_source = select(Listen.source, func.count(Listen.id).label("cnt"))\
            .group_by(Listen.source)\
            .order_by(desc("cnt"))\
            .limit(1)
        source_row = conn.execute(stmt_source).first()
        top_source = source_row.source if source_row else "unknown"
        
        # Average per day
        avg_per_day = round(total_listens / days_active, 1) if days_active > 0 else 0

        # Oldest year
        min_ts = conn.execute(select(func.min(Listen.unix_ts))).scalar()
        first_year = datetime.fromtimestamp(min_ts, tz=timezone.utc).year if min_ts else datetime.now().year
        
        return {
            "total_listens": total_listens,
            "unique_artists": unique_artists,
            "unique_tracks": unique_tracks,
            "days_active": days_active,
            "avg_per_day": avg_per_day,
            "top_source": top_source,
            "db_type": db_type,
            "first_year": first_year
        }

def get_time_range_filter(time_range_days: str):
    """Generate SQLAlchemy filter condition for a day-based time range."""
    if not time_range_days or time_range_days == "all":
        return None
    try:
        days = int(time_range_days)
        cutoff = int(datetime.now(timezone.utc).timestamp()) - (days * 86400)
        return Listen.unix_ts >= cutoff
    except ValueError:
        return None

def get_top_artists(time_range: str = "all", limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve top artists for a given time range."""
    with get_engine().connect() as conn:
        stmt = select(Listen.artist, func.count(Listen.id).label("play_count"))
        filter_cond = get_time_range_filter(time_range)
        if filter_cond is not None:
            stmt = stmt.where(filter_cond)
        stmt = stmt.group_by(Listen.artist)\
            .order_by(desc("play_count"))\
            .limit(limit)
        
        rows = conn.execute(stmt).all()
        return [{"artist": r.artist, "play_count": r.play_count} for r in rows]

def get_top_tracks(time_range: str = "all", limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve top tracks for a given time range."""
    with get_engine().connect() as conn:
        stmt = select(Listen.artist, Listen.title, func.count(Listen.id).label("play_count"))
        filter_cond = get_time_range_filter(time_range)
        if filter_cond is not None:
            stmt = stmt.where(filter_cond)
        stmt = stmt.group_by(Listen.artist, Listen.title)\
            .order_by(desc("play_count"))\
            .limit(limit)
            
        rows = conn.execute(stmt).all()
        return [{"artist": r.artist, "title": r.title, "play_count": r.play_count} for r in rows]

def get_heatmap_data(year: int | str | None = None) -> dict[str, int]:
    """Retrieve counts of scrobbles grouped by date (YYYY-MM-DD) for a given year."""
    if not year:
        year = str(datetime.now().year)
        
    date_expr = get_date_expr(Listen.unix_ts)
    year_expr = get_year_expr(Listen.unix_ts)
    
    with get_engine().connect() as conn:
        stmt = select(date_expr.label("day"), func.count(Listen.id).label("cnt"))\
            .where(year_expr == str(year))\
            .group_by(date_expr)
            
        rows = conn.execute(stmt).all()
        return {r.day: r.cnt for r in rows if r.day}

def get_hourly_trends() -> dict[str, int]:
    """Retrieve play counts grouped by hour of the day (00-23) in local time."""
    hour_expr = get_hour_expr(Listen.unix_ts)
    
    with get_engine().connect() as conn:
        stmt = select(hour_expr.label("hour"), func.count(Listen.id).label("cnt"))\
            .group_by(hour_expr)\
            .order_by("hour")
            
        rows = conn.execute(stmt).all()
        
        # Initialize all 24 hours
        trends = {f"{h:02d}": 0 for h in range(24)}
        for r in rows:
            if r.hour:
                trends[r.hour] = r.cnt
        return trends

def get_punchcard_data() -> dict[str, int]:
    """Retrieve play counts grouped by day-of-week (0=Sun) and hour (00-23) in local time."""
    dow_expr = get_day_of_week_expr(Listen.unix_ts)
    hour_expr = get_hour_expr(Listen.unix_ts)

    with get_engine().connect() as conn:
        stmt = select(dow_expr.label("dow"), hour_expr.label("hour"), func.count(Listen.id).label("cnt"))\
            .group_by(dow_expr, hour_expr)

        rows = conn.execute(stmt).all()

        # Initialize all 168 cells (7 days × 24 hours)
        trends: dict[str, int] = {f"{d}_{h:02d}": 0 for d in range(7) for h in range(24)}
        for r in rows:
            if r.dow is not None and r.hour is not None:
                trends[f"{int(r.dow)}_{r.hour}"] = r.cnt
        return trends

def get_monthly_trends() -> list[dict[str, Any]]:
    """Retrieve play counts grouped by month (YYYY-MM) in local time."""
    month_expr = get_month_expr(Listen.unix_ts)
    
    with get_engine().connect() as conn:
        stmt = select(month_expr.label("month"), func.count(Listen.id).label("cnt"))\
            .group_by(month_expr)\
            .order_by("month")
            
        rows = conn.execute(stmt).all()
        return [{"month": r.month, "count": r.cnt} for r in rows if r.month]

def get_streak_stats() -> dict[str, int]:
    """Calculate the current active streak and all-time longest consecutive listening streak (in days)."""
    date_expr = get_date_expr(Listen.unix_ts)
    
    with get_engine().connect() as conn:
        stmt = select(distinct(date_expr).label("day"))\
            .order_by("day")
            
        rows = conn.execute(stmt).all()
        days = [datetime.strptime(r.day, "%Y-%m-%d").date() for r in rows if r.day]
    
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
    today = get_current_local_date()
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

def get_wrapped_data(year: int | None, quarter: str | None = None, month: str | None = None) -> dict[str, Any]:
    """
    Retrieve highly detailed spotify-wrapped style metrics for custom periods.
    Supports years, quarters (Q1-Q4), specific months (M1-M12).
    """
    year_expr = get_year_expr(Listen.unix_ts)
    month_num_expr = get_month_num_expr(Listen.unix_ts)
    
    filters = []
    
    # 1. Filter by year
    if year is not None:
        filters.append(year_expr == str(year))
        
    # 2. Filter by quarter
    if quarter:
        if quarter == "Q1":
            filters.append(month_num_expr.in_([1, 2, 3]))
        elif quarter == "Q2":
            filters.append(month_num_expr.in_([4, 5, 6]))
        elif quarter == "Q3":
            filters.append(month_num_expr.in_([7, 8, 9]))
        elif quarter == "Q4":
            filters.append(month_num_expr.in_([10, 11, 12]))
            
    # 3. Filter by month
    if month:
        m_int = int(month.replace("M", ""))
        filters.append(month_num_expr == m_int)
        
    with get_engine().connect() as conn:
        # A. Total plays
        stmt_count = select(func.count(Listen.id)).where(*filters)
        total_plays = conn.execute(stmt_count).scalar() or 0
        
        if total_plays == 0:
            return {
                "total_plays": 0, "top_artist": None, "top_track": None,
                "peak_day": None, "minutes_listened": 0
            }
            
        # B. Top Artist
        stmt_artist = select(Listen.artist, func.count(Listen.id).label("cnt"))\
            .where(*filters)\
            .group_by(Listen.artist)\
            .order_by(desc("cnt"))\
            .limit(1)
        artist_row = conn.execute(stmt_artist).first()
        top_artist = {"name": artist_row.artist, "plays": artist_row.cnt} if artist_row else None
        
        # C. Top Track
        stmt_track = select(Listen.artist, Listen.title, func.count(Listen.id).label("cnt"))\
            .where(*filters)\
            .group_by(Listen.artist, Listen.title)\
            .order_by(desc("cnt"))\
            .limit(1)
        track_row = conn.execute(stmt_track).first()
        top_track = {"artist": track_row.artist, "title": track_row.title, "plays": track_row.cnt} if track_row else None
        
        # D. Peak Listening Day
        date_expr = get_date_expr(Listen.unix_ts)
        stmt_peak = select(date_expr.label("day"), func.count(Listen.id).label("cnt"))\
            .where(*filters)\
            .group_by(date_expr)\
            .order_by(desc("cnt"))\
            .limit(1)
        day_row = conn.execute(stmt_peak).first()
        peak_day = {"date": day_row.day, "plays": day_row.cnt} if day_row else None
        
        # E. Minutes Listened Estimate (industry average 3.5 minutes per play)
        minutes_listened = round(total_plays * 3.5)
        
        return {
            "total_plays": total_plays,
            "top_artist": top_artist,
            "top_track": top_track,
            "peak_day": peak_day,
            "minutes_listened": minutes_listened
        }

def get_recent_listens(
    limit: int = 50,
    before_ts: int | None = None,
    before_id: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve recent listens in reverse-chronological order using cursor-based keyset pagination.

    Pass before_ts and before_id (from the last item of the previous page) to get the next page.
    """
    with get_engine().connect() as conn:
        stmt = select(Listen.id, Listen.artist, Listen.title, Listen.unix_ts, Listen.source)
        if before_ts is not None and before_id is not None:
            stmt = stmt.where(tuple_(Listen.unix_ts, Listen.id) < (before_ts, before_id))
        stmt = stmt.order_by(desc(Listen.unix_ts), desc(Listen.id)).limit(limit)
        rows = conn.execute(stmt).all()
        return [
            {"id": r.id, "artist": r.artist, "title": r.title, "unix_ts": r.unix_ts, "source": r.source}
            for r in rows
        ]

def get_track_play_count(artist: str, title: str) -> int:
    """Count all-time plays for a specific artist + title combination."""
    with get_engine().connect() as conn:
        result = conn.execute(
            select(func.count(Listen.id)).where(
                Listen.artist == artist,
                Listen.title == title,
            )
        ).scalar()
        return result or 0

def get_on_this_day(month: int, day: int) -> list[dict[str, Any]]:
    """Retrieve listens for today's calendar date across all prior years (excluding current year), grouped by year."""
    month_expr = get_month_num_expr(Listen.unix_ts)
    day_expr = get_day_num_expr(Listen.unix_ts)
    year_expr = get_year_expr(Listen.unix_ts)
    current_year = datetime.now().year

    with get_engine().connect() as conn:
        stmt = (
            select(
                Listen.id, Listen.artist, Listen.title, Listen.unix_ts, Listen.source,
                year_expr.label("year"),
            )
            .where(month_expr == month, day_expr == day)
            .order_by(desc(Listen.unix_ts))
        )
        rows = conn.execute(stmt).all()

    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if int(r.year) == current_year:
            continue
        groups.setdefault(str(r.year), []).append(
            {"id": r.id, "artist": r.artist, "title": r.title, "unix_ts": r.unix_ts, "source": r.source}
        )
    return [{"year": int(k), "listens": v} for k, v in groups.items()]

def deduplicate_listens() -> int:
    """
    Remove duplicate listens where the same artist and title are scrobbled
    within 60 seconds of each other. Keeps the entry with the lower ID.
    Returns the number of deleted duplicate rows.
    """
    with get_engine().begin() as conn:
        stmt = """
            DELETE FROM listens 
            WHERE id IN (
                SELECT b.id 
                FROM listens a 
                JOIN listens b ON a.artist = b.artist 
                              AND a.title = b.title 
                              AND a.id < b.id 
                              AND abs(a.unix_ts - b.unix_ts) <= 60
            )
        """
        res = conn.execute(text(stmt))
        return res.rowcount
