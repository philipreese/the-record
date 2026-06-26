import logging
from datetime import datetime, date, timezone, timedelta
from typing import Any, List, Optional
import os
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, desc, distinct, text, tuple_, or_, and_
from app.db import get_engine, Listen
from app.db_helpers import IS_POSTGRES, get_date_expr, get_hour_expr, get_month_expr, get_month_num_expr, get_day_num_expr, get_year_expr, get_day_of_week_expr
from app.schemas import (
    ArtistAnniversary,
    ArtistInfo,
    ArtistMonthlyTrend,
    ArtistStatsResponse,
    ArtistTopTrack,
    ArtistTrendResponse,
    ArtistTrendSeries,
    ListenEntry,
    MonthlyTrendInfo,
    OnRepeatPeak,
    OnThisDayGroup,
    OnThisDayResponse,
    StatsSummaryResponse,
    StreakStatsResponse,
    TopArtistsResponse,
    TopArtistTrendsResponse,
    TopTracksResponse,
    TrackBatchResponseItem,
    TrackInfo,
    TrackMonthlyTrend,
    TrackTrendSeries,
    WeeklyBreakdownItem,
    WrappedArtist,
    WrappedDataResponse,
    WrappedPeakDay,
    WrappedTrack,
)

logger = logging.getLogger(__name__)

def get_current_local_date() -> date:
    """Resolve the current calendar date in the configured TZ timezone, falling back to local system date."""
    tz_name = os.environ.get("TZ")
    if tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            pass
    return datetime.now().date()

def get_stats_summary() -> StatsSummaryResponse:
    """Calculate overall statistics from the scrobble database."""
    with get_engine().connect() as conn:
        # Total count
        total_listens = conn.execute(select(func.count(Listen.id))).scalar() or 0

        db_type = "PostgreSQL (Neon)" if IS_POSTGRES else "SQLite (Local)"

        if total_listens == 0:
            return StatsSummaryResponse(
                total_listens=0, unique_artists=0, unique_tracks=0,
                days_active=0, avg_per_day=0.0, top_source="None",
                db_type=db_type,
            )

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

        return StatsSummaryResponse(
            total_listens=total_listens,
            unique_artists=unique_artists,
            unique_tracks=unique_tracks,
            days_active=days_active,
            avg_per_day=avg_per_day,
            top_source=top_source,
            db_type=db_type,
            first_year=first_year,
        )

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
def get_top_artists(
    time_range: str = "all",
    limit: int = 15,
    page: int = 1,
    search: Optional[str] = None
) -> TopArtistsResponse:
    """Retrieve top artists with absolute rank, search filtering, pagination, and total count."""
    offset = (page - 1) * limit
    with get_engine().connect() as conn:
        # Step 1: Subquery to compute absolute rank for all artists in the chosen time range
        agg_stmt = select(
            Listen.artist,
            func.count(Listen.id).label("play_count"),
            func.rank().over(order_by=desc(func.count(Listen.id))).label("rank")
        )
        
        filter_cond = get_time_range_filter(time_range)
        if filter_cond is not None:
            agg_stmt = agg_stmt.where(filter_cond)
            
        agg_stmt = agg_stmt.group_by(Listen.artist)
        subq = agg_stmt.subquery()
        
        # Step 2: Outer select with search filtering and pagination
        stmt = select(subq.c.artist, subq.c.play_count, subq.c.rank)
        if search:
            stmt = stmt.where(subq.c.artist.ilike(f"%{search}%"))
            
        # Count total filtered items
        count_stmt = select(func.count()).select_from(subq)
        if search:
            count_stmt = count_stmt.where(subq.c.artist.ilike(f"%{search}%"))
        total_count = conn.execute(count_stmt).scalar() or 0

        stmt = stmt.order_by(subq.c.rank, subq.c.artist).limit(limit).offset(offset)
        
        rows = conn.execute(stmt).all()
        items = [ArtistInfo(artist=r.artist, play_count=r.play_count, rank=r.rank) for r in rows]
        return TopArtistsResponse(items=items, total_count=total_count)

def get_top_tracks(
    time_range: str = "all",
    limit: int = 15,
    page: int = 1,
    search: Optional[str] = None
) -> TopTracksResponse:
    """Retrieve top tracks with absolute rank, search filtering, pagination, and total count."""
    offset = (page - 1) * limit
    with get_engine().connect() as conn:
        # Step 1: Subquery to compute absolute rank for all tracks in the chosen time range
        agg_stmt = select(
            Listen.artist,
            Listen.title,
            func.count(Listen.id).label("play_count"),
            func.rank().over(order_by=desc(func.count(Listen.id))).label("rank")
        )
        
        filter_cond = get_time_range_filter(time_range)
        if filter_cond is not None:
            agg_stmt = agg_stmt.where(filter_cond)
            
        agg_stmt = agg_stmt.group_by(Listen.artist, Listen.title)
        subq = agg_stmt.subquery()
        
        # Step 2: Outer select with search filtering and pagination
        stmt = select(subq.c.artist, subq.c.title, subq.c.play_count, subq.c.rank)
        if search:
            stmt = stmt.where(
                or_(
                    subq.c.artist.ilike(f"%{search}%"),
                    subq.c.title.ilike(f"%{search}%")
                )
            )
            
        # Count total filtered items
        count_stmt = select(func.count()).select_from(subq)
        if search:
            count_stmt = count_stmt.where(
                or_(
                    subq.c.artist.ilike(f"%{search}%"),
                    subq.c.title.ilike(f"%{search}%")
                )
            )
        total_count = conn.execute(count_stmt).scalar() or 0

        stmt = stmt.order_by(subq.c.rank, subq.c.artist, subq.c.title).limit(limit).offset(offset)
        
        rows = conn.execute(stmt).all()
        items = [TrackInfo(artist=r.artist, title=r.title, play_count=r.play_count, rank=r.rank) for r in rows]
        return TopTracksResponse(items=items, total_count=total_count)


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

def get_monthly_trends() -> list[MonthlyTrendInfo]:
    """Retrieve play counts grouped by month (YYYY-MM) in local time."""
    month_expr = get_month_expr(Listen.unix_ts)
    
    with get_engine().connect() as conn:
        stmt = select(month_expr.label("month"), func.count(Listen.id).label("cnt"))\
            .group_by(month_expr)\
            .order_by("month")
            
        rows = conn.execute(stmt).all()
        return [MonthlyTrendInfo(month=r.month, count=r.cnt) for r in rows if r.month]

def get_streak_stats() -> StreakStatsResponse:
    """Calculate the current active streak and all-time longest consecutive listening streak (in days)."""
    date_expr = get_date_expr(Listen.unix_ts)
    
    with get_engine().connect() as conn:
        stmt = select(distinct(date_expr).label("day"))\
            .order_by("day")
            
        rows = conn.execute(stmt).all()
        days = [datetime.strptime(r.day, "%Y-%m-%d").date() for r in rows if r.day]
    
    if not days:
        return StreakStatsResponse(current_streak=0, longest_streak=0)
        
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
            
    return StreakStatsResponse(current_streak=current_streak, longest_streak=max(longest, current_streak))

def get_wrapped_data(year: int | None, quarter: str | None = None, month: str | None = None) -> WrappedDataResponse:
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
            return WrappedDataResponse(
                total_plays=0, top_artist=None, top_track=None,
                peak_day=None, minutes_listened=0, on_repeat_peak=None,
            )
            
        # B. Top Artist
        stmt_artist = select(Listen.artist, func.count(Listen.id).label("cnt"))\
            .where(*filters)\
            .group_by(Listen.artist)\
            .order_by(desc("cnt"))\
            .limit(1)
        artist_row = conn.execute(stmt_artist).first()
        top_artist = WrappedArtist(name=artist_row.artist, plays=artist_row.cnt) if artist_row else None

        # C. Top Track
        stmt_track = select(Listen.artist, Listen.title, func.count(Listen.id).label("cnt"))\
            .where(*filters)\
            .group_by(Listen.artist, Listen.title)\
            .order_by(desc("cnt"))\
            .limit(1)
        track_row = conn.execute(stmt_track).first()
        top_track = WrappedTrack(artist=track_row.artist, title=track_row.title, plays=track_row.cnt) if track_row else None

        # D. Peak Listening Day
        date_expr = get_date_expr(Listen.unix_ts)
        stmt_peak = select(date_expr.label("day"), func.count(Listen.id).label("cnt"))\
            .where(*filters)\
            .group_by(date_expr)\
            .order_by(desc("cnt"))\
            .limit(1)
        day_row = conn.execute(stmt_peak).first()
        peak_day = WrappedPeakDay(date=day_row.day, plays=day_row.cnt) if day_row else None

        # E. Minutes Listened (true duration sum falling back to 3.5-min estimate for nulls)
        stmt_duration = select(func.sum(func.coalesce(Listen.duration_secs, 210))).where(*filters)
        total_seconds = conn.execute(stmt_duration).scalar() or 0
        minutes_listened = round(total_seconds / 60)

        # F. On-Repeat Peak — max plays of one track on a single day
        # Group by lowercased artist/title so casing variants (YT Music vs LB) are merged.
        # func.min() picks a representative display value from the matching rows.
        stmt_on_repeat = (
            select(
                date_expr.label("day"),
                func.min(Listen.artist).label("artist"),
                func.min(Listen.title).label("title"),
                func.count(Listen.id).label("cnt"),
            )
            .where(*filters)
            .group_by(date_expr, func.lower(Listen.artist), func.lower(Listen.title))
            .order_by(desc("cnt"))
            .limit(1)
        )
        on_repeat_row = conn.execute(stmt_on_repeat).first()
        on_repeat_peak = (
            OnRepeatPeak(
                artist=on_repeat_row.artist,
                title=on_repeat_row.title,
                date=on_repeat_row.day,
                count=on_repeat_row.cnt,
            )
            if on_repeat_row
            else None
        )

        return WrappedDataResponse(
            total_plays=total_plays,
            top_artist=top_artist,
            top_track=top_track,
            peak_day=peak_day,
            minutes_listened=minutes_listened,
            on_repeat_peak=on_repeat_peak,
        )

def get_recent_listens(
    limit: int = 50,
    before_ts: int | None = None,
    before_id: int | None = None,
    anchor_date: Optional[str] = None,
) -> list[ListenEntry]:
    """Retrieve recent listens in reverse-chronological order using cursor-based keyset pagination.

    Pass before_ts and before_id (from the last item of the previous page) to get the next page.
    """
    with get_engine().connect() as conn:
        stmt = select(
            Listen.id,
            Listen.artist,
            Listen.title,
            Listen.unix_ts,
            Listen.source,
            Listen.duration_secs,
            Listen.album,
            Listen.recording_mbid,
        )
        if before_ts is not None and before_id is not None:
            stmt = stmt.where(tuple_(Listen.unix_ts, Listen.id) < (before_ts, before_id))
        elif anchor_date is not None:
            try:
                dt = datetime.strptime(anchor_date, "%Y-%m-%d")
                dt_end = datetime.combine(dt.date(), datetime.max.time())
                tz_name = os.environ.get("TZ")
                if tz_name:
                    try:
                        from zoneinfo import ZoneInfo
                        dt_end = dt_end.replace(tzinfo=ZoneInfo(tz_name))
                    except Exception:
                        dt_end = dt_end.astimezone()
                else:
                    dt_end = dt_end.astimezone()
                anchor_ts = int(dt_end.timestamp())
                stmt = stmt.where(Listen.unix_ts <= anchor_ts)
            except ValueError:
                logger.warning("Invalid anchor_date format: %r", anchor_date)
        stmt = stmt.order_by(desc(Listen.unix_ts), desc(Listen.id)).limit(limit)
        rows = conn.execute(stmt).all()
        return [
            ListenEntry(id=r.id, artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                        source=r.source, duration_secs=r.duration_secs, album=r.album,
                        recording_mbid=r.recording_mbid)
            for r in rows
        ]

def get_track_stats(
    artist: str,
    title: str,
    album: Optional[str] = None,
    recording_mbid: Optional[str] = None,
) -> tuple[int, Optional[int]]:
    """Get the all-time play count and first available non-null duration for a track.

    When ``recording_mbid`` is supplied, it is used as the canonical track identity:
    rows carrying that MBID are counted together with any not-yet-backfilled rows
    that match on (artist, title) but have a null MBID. This merges inconsistent
    artist-credit variants (e.g. "Beartooth & Hardy" vs "Beartooth"). The ``album``
    scope is ignored in this case since the MBID already identifies the recording.
    """
    string_match = and_(
        func.lower(Listen.artist) == artist.lower(),
        func.lower(Listen.title) == title.lower(),
    )
    with get_engine().connect() as conn:
        if recording_mbid:
            filters = [
                or_(
                    Listen.recording_mbid == recording_mbid,
                    and_(Listen.recording_mbid.is_(None), string_match),
                )
            ]
        else:
            filters = [string_match]
            if album is not None:
                filters.append(or_(Listen.album == album, Listen.album.is_(None)))

        play_count = conn.execute(
            select(func.count(Listen.id)).where(*filters)
        ).scalar() or 0

        duration = conn.execute(
            select(Listen.duration_secs)
            .where(*filters, Listen.duration_secs.isnot(None))
            .limit(1)
        ).scalar()

        return play_count, duration

def get_track_play_count(artist: str, title: str, recording_mbid: Optional[str] = None) -> int:
    """Count all-time plays for a specific track, optionally by canonical recording MBID."""
    count, _ = get_track_stats(artist, title, recording_mbid=recording_mbid)
    return count

def get_track_stats_batch(tracks: list[dict[str, str]]) -> list[TrackBatchResponseItem]:
    """Get the all-time play count and first available non-null duration for a list of tracks in a single batch query."""
    if not tracks:
        return []
        
    seen = set()
    unique_pairs = []
    for t in tracks:
        a_low = t["artist"].lower()
        t_low = t["title"].lower()
        if (a_low, t_low) not in seen:
            seen.add((a_low, t_low))
            unique_pairs.append({"artist": t["artist"], "title": t["title"]})
            
    from sqlalchemy import and_, or_
    
    stmt = select(
        func.lower(Listen.artist).label("artist_lower"),
        func.lower(Listen.title).label("title_lower"),
        func.count(Listen.id).label("play_count"),
        func.max(Listen.duration_secs).label("duration_secs")
    ).where(
        or_(*(
            and_(
                func.lower(Listen.artist) == p["artist"].lower(),
                func.lower(Listen.title) == p["title"].lower()
            )
            for p in unique_pairs
        ))
    ).group_by(func.lower(Listen.artist), func.lower(Listen.title))
    
    counts_map = {}
    with get_engine().connect() as conn:
        rows = conn.execute(stmt).all()
        for r in rows:
            counts_map[(r.artist_lower, r.title_lower)] = (r.play_count, r.duration_secs)
            
    result = []
    for t in tracks:
        key = (t["artist"].lower(), t["title"].lower())
        play_count, duration = counts_map.get(key, (0, None))
        result.append(TrackBatchResponseItem(
            artist=t["artist"], title=t["title"],
            play_count=play_count, duration_secs=duration,
        ))

    return result

def get_on_this_day_anniversaries(month: int, day: int) -> list[ArtistAnniversary]:
    """Find artists whose first-ever listen anniversary falls on the given month/day (excluding current year)."""
    current_year = datetime.now().year

    with get_engine().connect() as conn:
        first_ts_subq = (
            select(
                Listen.artist,
                func.min(Listen.unix_ts).label("first_ts"),
                func.count(Listen.id).label("total_plays"),
            )
            .group_by(Listen.artist)
            .subquery()
        )
        month_expr = get_month_num_expr(first_ts_subq.c.first_ts)
        day_expr = get_day_num_expr(first_ts_subq.c.first_ts)
        stmt = (
            select(
                first_ts_subq.c.artist,
                first_ts_subq.c.first_ts,
                first_ts_subq.c.total_plays,
            )
            .where(month_expr == month, day_expr == day)
            .order_by(desc(first_ts_subq.c.total_plays))
        )
        rows = conn.execute(stmt).all()

    result = []
    for r in rows:
        dt = datetime.fromtimestamp(r.first_ts, tz=timezone.utc)
        if dt.year < current_year:
            result.append(ArtistAnniversary(
                artist=r.artist,
                first_listen_ts=r.first_ts,
                years=current_year - dt.year,
                total_plays=r.total_plays,
            ))
    return result


def get_on_this_day(month: int, day: int) -> OnThisDayResponse:
    """Retrieve listens for today's calendar date across all prior years (excluding current year), grouped by year."""
    month_expr = get_month_num_expr(Listen.unix_ts)
    day_expr = get_day_num_expr(Listen.unix_ts)
    year_expr = get_year_expr(Listen.unix_ts)
    current_year = datetime.now().year

    with get_engine().connect() as conn:
        stmt = (
            select(
                Listen.id, Listen.artist, Listen.title, Listen.unix_ts, Listen.source,
                Listen.duration_secs, Listen.album, Listen.recording_mbid,
                year_expr.label("year"),
            )
            .where(month_expr == month, day_expr == day)
            .order_by(desc(Listen.unix_ts))
        )
        rows = conn.execute(stmt).all()

    groups: dict[str, list[ListenEntry]] = {}
    for r in rows:
        if int(r.year) == current_year:
            continue
        groups.setdefault(str(r.year), []).append(
            ListenEntry(id=r.id, artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                        source=r.source, duration_secs=r.duration_secs, album=r.album,
                        recording_mbid=r.recording_mbid)
        )
    group_list = [OnThisDayGroup(year=int(k), listens=v) for k, v in groups.items()]
    anniversaries = get_on_this_day_anniversaries(month, day)
    return OnThisDayResponse(groups=group_list, anniversaries=anniversaries)

def get_export_data(range_days: str = "all") -> list[dict[str, Any]]:
    """Return all listen rows (or a time-filtered subset) sorted by unix_ts ascending."""
    with get_engine().connect() as conn:
        stmt = select(
            Listen.id,
            Listen.artist,
            Listen.title,
            Listen.album,
            Listen.unix_ts,
            Listen.source,
            Listen.duration_secs,
        ).order_by(Listen.unix_ts)
        f = get_time_range_filter(range_days)
        if f is not None:
            stmt = stmt.where(f)
        rows = conn.execute(stmt).all()
    return [
        {
            "id": r.id,
            "artist": r.artist,
            "title": r.title,
            "album": r.album,
            "unix_ts": r.unix_ts,
            "datetime_utc": datetime.fromtimestamp(r.unix_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": r.source,
            "duration_secs": r.duration_secs,
        }
        for r in rows
    ]


def get_listens_by_day(date_str: str) -> list[ListenEntry]:
    """Return all listens for a local-timezone calendar date (YYYY-MM-DD) in chronological order."""
    date_expr = get_date_expr(Listen.unix_ts)
    with get_engine().connect() as conn:
        stmt = (
            select(
                Listen.id,
                Listen.artist,
                Listen.title,
                Listen.unix_ts,
                Listen.source,
                Listen.duration_secs,
                Listen.album,
            )
            .where(date_expr == date_str)
            .order_by(Listen.unix_ts.asc(), Listen.id.asc())
        )
        rows = conn.execute(stmt).all()
        return [
            ListenEntry(id=r.id, artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                        source=r.source, duration_secs=r.duration_secs, album=r.album)
            for r in rows
        ]


def get_weekly_breakdown(year: int, month: int) -> list[WeeklyBreakdownItem]:
    """Return play counts grouped by week-of-month (1–5) for a given year and month."""
    month_str = f"{year}-{month:02d}"
    month_expr = get_month_expr(Listen.unix_ts)
    day_num_expr = get_day_num_expr(Listen.unix_ts)

    with get_engine().connect() as conn:
        stmt = (
            select(day_num_expr.label("day_num"), func.count(Listen.id).label("cnt"))
            .where(month_expr == month_str)
            .group_by(day_num_expr)
            .order_by(day_num_expr)
        )
        rows = conn.execute(stmt).all()

    weeks: dict[int, int] = {}
    for r in rows:
        week_num = (int(r.day_num) - 1) // 7 + 1
        weeks[week_num] = weeks.get(week_num, 0) + r.cnt

    return [WeeklyBreakdownItem(week=w, count=weeks[w]) for w in sorted(weeks.keys())]


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
                JOIN listens b ON LOWER(a.artist) = LOWER(b.artist)
                              AND LOWER(a.title)  = LOWER(b.title)
                              AND a.id < b.id
                              AND abs(a.unix_ts - b.unix_ts) <= 60
            )
        """
        res = conn.execute(text(stmt))
        return res.rowcount


def apply_artist_corrections() -> int:
    """Bulk-update listens whose artist name matches a row in artist_corrections.

    Returns the number of rows updated. Safe to call after every sync — the
    corrections table survives mirror syncs, so cleaned data is always restored.
    """
    with get_engine().begin() as conn:
        if IS_POSTGRES:
            result = conn.execute(text("""
                UPDATE listens
                SET artist = ac.correct_name
                FROM artist_corrections ac
                WHERE LOWER(listens.artist) = LOWER(ac.wrong_name)
            """))
        else:
            result = conn.execute(text("""
                UPDATE listens
                SET artist = (
                    SELECT correct_name FROM artist_corrections
                    WHERE LOWER(wrong_name) = LOWER(listens.artist)
                    LIMIT 1
                )
                WHERE LOWER(artist) IN (SELECT LOWER(wrong_name) FROM artist_corrections)
            """))
        return result.rowcount


def get_top_artist_trends(year: int, limit: int = 5) -> TopArtistTrendsResponse:
    """Retrieve top artists with their monthly breakdowns for a given year."""
    year_str = str(year)
    year_expr = get_year_expr(Listen.unix_ts)
    month_expr = get_month_expr(Listen.unix_ts)

    with get_engine().connect() as conn:
        # 1. Get top N artists by play count in that year
        stmt_top = (
            select(Listen.artist, func.count(Listen.id).label("play_count"))
            .where(year_expr == year_str)
            .group_by(Listen.artist)
            .order_by(desc("play_count"))
            .limit(limit)
        )
        top_rows = conn.execute(stmt_top).all()
        if not top_rows:
            return TopArtistTrendsResponse(year=year, trends=[])

        top_artists = [r.artist for r in top_rows]
        artist_play_counts = {r.artist: r.play_count for r in top_rows}

        # 2. Get monthly breakdowns for these top artists in a single query
        stmt_breakdown = (
            select(
                Listen.artist,
                month_expr.label("month"),
                func.count(Listen.id).label("cnt")
            )
            .where(year_expr == year_str, Listen.artist.in_(top_artists))
            .group_by(Listen.artist, month_expr)
        )
        breakdown_rows = conn.execute(stmt_breakdown).all()

    # Pre-populate all 12 months for every artist
    months = [f"{year}-{m:02d}" for m in range(1, 13)]
    artist_data = {
        artist: {m: 0 for m in months}
        for artist in top_artists
    }

    for r in breakdown_rows:
        if r.artist in artist_data and r.month in artist_data[r.artist]:
            artist_data[r.artist][r.month] = r.cnt

    trends = []
    for artist in top_artists:
        monthly_counts = [ArtistMonthlyTrend(month=m, count=artist_data[artist][m]) for m in months]
        trends.append(ArtistTrendSeries(
            artist=artist,
            play_count=artist_play_counts[artist],
            monthly_counts=monthly_counts,
        ))

    return TopArtistTrendsResponse(year=year, trends=trends)


def get_artist_stats(artist: str, time_range: str = "all") -> ArtistStatsResponse:
    """Get comprehensive listening stats for a specific artist."""
    artist_filter = func.lower(Listen.artist) == artist.lower()
    range_filter = get_time_range_filter(time_range)

    filters = [artist_filter]
    if range_filter is not None:
        filters.append(range_filter)

    with get_engine().connect() as conn:
        total_plays = conn.execute(
            select(func.count(Listen.id)).where(*filters)
        ).scalar() or 0

        if total_plays == 0:
            return ArtistStatsResponse(
                artist=artist,
                total_plays=0,
                rank=None,
                top_tracks=[],
                monthly_trends=[],
                peak_day=None,
                hourly={f"{h:02d}": 0 for h in range(24)},
                first_listen_ts=None,
            )

        # All-time rank (ignores time_range)
        rank_subq = (
            select(
                Listen.artist,
                func.count(Listen.id).label("cnt"),
                func.rank().over(order_by=desc(func.count(Listen.id))).label("rank"),
            )
            .group_by(Listen.artist)
            .subquery()
        )
        rank_row = conn.execute(
            select(rank_subq.c.rank).where(func.lower(rank_subq.c.artist) == artist.lower())
        ).first()
        rank = rank_row.rank if rank_row else None

        # All tracks in selected time range with timestamps, album, and duration
        stmt_tracks = (
            select(
                Listen.title,
                func.count(Listen.id).label("play_count"),
                func.min(Listen.unix_ts).label("first_ts"),
                func.max(Listen.unix_ts).label("last_ts"),
                func.max(Listen.album).label("album"),
                func.max(Listen.duration_secs).label("duration_secs"),
            )
            .where(*filters)
            .group_by(Listen.title)
            .order_by(desc("play_count"))
        )
        top_tracks = [
            ArtistTopTrack(
                title=r.title, play_count=r.play_count,
                first_listen_ts=r.first_ts, last_listen_ts=r.last_ts,
                album=r.album, duration_secs=r.duration_secs,
            )
            for r in conn.execute(stmt_tracks).all()
        ]

        # Monthly trends in selected time range
        month_expr = get_month_expr(Listen.unix_ts)
        stmt_monthly = (
            select(month_expr.label("month"), func.count(Listen.id).label("cnt"))
            .where(*filters)
            .group_by(month_expr)
            .order_by("month")
        )
        monthly_trends = [
            ArtistMonthlyTrend(month=r.month, count=r.cnt)
            for r in conn.execute(stmt_monthly).all()
            if r.month
        ]

        # Peak day in selected time range
        date_expr = get_date_expr(Listen.unix_ts)
        stmt_peak = (
            select(date_expr.label("day"), func.count(Listen.id).label("cnt"))
            .where(*filters)
            .group_by(date_expr)
            .order_by(desc("cnt"))
            .limit(1)
        )
        day_row = conn.execute(stmt_peak).first()
        peak_day = WrappedPeakDay(date=day_row.day, plays=day_row.cnt) if day_row else None

        # Hourly distribution in selected time range
        hour_expr = get_hour_expr(Listen.unix_ts)
        stmt_hourly = (
            select(hour_expr.label("hour"), func.count(Listen.id).label("cnt"))
            .where(*filters)
            .group_by(hour_expr)
            .order_by("hour")
        )
        hourly: dict[str, int] = {f"{h:02d}": 0 for h in range(24)}
        for r in conn.execute(stmt_hourly).all():
            if r.hour:
                hourly[r.hour] = r.cnt

        # First listen timestamp and all-time plays — always all-time, ignores time_range
        all_time_row = conn.execute(
            select(func.min(Listen.unix_ts), func.count(Listen.id))
            .where(func.lower(Listen.artist) == artist.lower())
        ).first()
        first_listen_ts = all_time_row[0] if all_time_row else None
        plays_since_discovery = all_time_row[1] if all_time_row else 0

    return ArtistStatsResponse(
        artist=artist,
        total_plays=total_plays,
        rank=rank,
        top_tracks=top_tracks,
        monthly_trends=monthly_trends,
        peak_day=peak_day,
        hourly=hourly,
        first_listen_ts=first_listen_ts,
        plays_since_discovery=plays_since_discovery,
    )


def get_artist_track_trends(artist: str, year: int, limit: int = 5) -> ArtistTrendResponse:
    """Retrieve top tracks of an artist with their monthly breakdowns for a given year."""
    year_str = str(year)
    year_expr = get_year_expr(Listen.unix_ts)
    month_expr = get_month_expr(Listen.unix_ts)

    with get_engine().connect() as conn:
        # 1. Get top N tracks for the artist by play count in that year
        stmt_top = (
            select(Listen.title, func.count(Listen.id).label("play_count"))
            .where(year_expr == year_str, func.lower(Listen.artist) == artist.lower())
            .group_by(Listen.title)
            .order_by(desc("play_count"))
            .limit(limit)
        )
        top_rows = conn.execute(stmt_top).all()
        if not top_rows:
            return ArtistTrendResponse(artist=artist, year=year, trends=[])

        top_tracks = [r.title for r in top_rows]
        track_play_counts = {r.title: r.play_count for r in top_rows}

        # 2. Get monthly breakdowns for these top tracks in a single query
        stmt_breakdown = (
            select(
                Listen.title,
                month_expr.label("month"),
                func.count(Listen.id).label("cnt")
            )
            .where(
                year_expr == year_str,
                func.lower(Listen.artist) == artist.lower(),
                Listen.title.in_(top_tracks)
            )
            .group_by(Listen.title, month_expr)
        )
        breakdown_rows = conn.execute(stmt_breakdown).all()

    # Pre-populate all 12 months for every track
    months = [f"{year}-{m:02d}" for m in range(1, 13)]
    track_data = {
        title: {m: 0 for m in months}
        for title in top_tracks
    }

    for r in breakdown_rows:
        if r.title in track_data and r.month in track_data[r.title]:
            track_data[r.title][r.month] = r.cnt

    trends = []
    for title in top_tracks:
        monthly_counts = [TrackMonthlyTrend(month=m, count=track_data[title][m]) for m in months]
        trends.append(TrackTrendSeries(
            track=title,
            play_count=track_play_counts[title],
            monthly_counts=monthly_counts,
        ))

    return ArtistTrendResponse(artist=artist, year=year, trends=trends)

