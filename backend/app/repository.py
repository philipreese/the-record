import logging
from datetime import datetime, date, timezone, timedelta
from typing import Any, List, Optional, cast
import os
from zoneinfo import ZoneInfo
from sqlalchemy import Boolean, Column, Integer, Table, Text, MetaData, select, func, desc, distinct, text, tuple_, or_, and_
from app.db import get_engine, get_session, Listen, CoverArtCache, ListenCorrection, CanonicalTrack, TrackRawKey
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

# SQLAlchemy Table proxy for the corrected_listens view so ORM helpers
# (get_date_expr, get_hour_expr, etc.) can reference its columns.
_cl = Table(
    "corrected_listens",
    MetaData(),
    Column("id", Integer),
    Column("unix_ts", Integer),
    Column("source", Text),
    Column("artist", Text),
    Column("title", Text),
    Column("album", Text),
    Column("duration_secs", Integer),
    Column("recording_mbid", Text),
    Column("artist_raw_folded", Text),
    Column("title_raw_folded", Text),
    Column("has_listen_correction", Boolean),
    Column("has_track_correction", Boolean),
    Column("track_id", Integer),
)


def get_current_local_date() -> date:
    """Resolve the current calendar date in the configured TZ timezone, falling back to local system date."""
    tz_name = os.environ.get("TZ")
    if tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name)).date()
        except Exception:
            pass
    return datetime.now().date()

def get_all_cover_art() -> dict[tuple[str, str], tuple[Optional[str], bool]]:
    """Load every cover art entry from the persistent DB cache.

    Returns a dict mapping (artist_folded, title_folded) to (url, manual_override).
    """
    with get_engine().connect() as conn:
        rows = conn.execute(select(CoverArtCache)).fetchall()
        return {
            (row.artist_folded, row.title_folded): (row.url, bool(row.manual_override))
            for row in rows
        }


def get_cover_art_batch(keys: list[tuple[str, str]]) -> dict[tuple[str, str], tuple[Optional[str], bool]]:
    """Look up a batch of (artist_folded, title_folded) keys from the DB cache.

    Returns only keys that exist in the DB (absent = never attempted).
    Each value is (url, manual_override).
    """
    if not keys:
        return {}
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(CoverArtCache).where(
                or_(*[
                    and_(CoverArtCache.artist_folded == k[0], CoverArtCache.title_folded == k[1])
                    for k in keys
                ])
            )
        ).fetchall()
    return {
        (row.artist_folded, row.title_folded): (row.url, bool(row.manual_override))
        for row in rows
    }


def upsert_cover_art(
    artist_folded: str,
    title_folded: str,
    url: Optional[str],
    manual_override: bool = False,
) -> None:
    """Insert or update a cover art URL in the persistent cache.

    manual_override=True marks the entry so background resolvers skip it.
    This flag is sticky — once True, subsequent calls with manual_override=False
    leave it True to prevent auto-resolution from overwriting user-set art.
    """
    with get_engine().begin() as conn:
        if IS_POSTGRES:
            conn.execute(
                text(
                    "INSERT INTO cover_art_cache (artist_folded, title_folded, url, original_url, manual_override)"
                    " VALUES (:af, :tf, :url, :url, :mo)"
                    " ON CONFLICT (artist_folded, title_folded) DO UPDATE SET"
                    "   url = excluded.url,"
                    "   original_url = COALESCE(cover_art_cache.original_url, excluded.url),"
                    "   manual_override = cover_art_cache.manual_override OR excluded.manual_override"
                ),
                {"af": artist_folded, "tf": title_folded, "url": url, "mo": manual_override},
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO cover_art_cache (artist_folded, title_folded, url, original_url, manual_override)"
                    " VALUES (:af, :tf, :url, :url, :mo)"
                    " ON CONFLICT (artist_folded, title_folded) DO UPDATE SET"
                    "   url = excluded.url,"
                    "   original_url = COALESCE(cover_art_cache.original_url, excluded.url),"
                    "   manual_override = MAX(cover_art_cache.manual_override, excluded.manual_override)"
                ),
                {"af": artist_folded, "tf": title_folded, "url": url, "mo": int(manual_override)},
            )


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
            _cl.c.id, _cl.c.artist, _cl.c.title, _cl.c.unix_ts,
            _cl.c.source, _cl.c.duration_secs, _cl.c.album, _cl.c.recording_mbid,
            _cl.c.has_listen_correction, _cl.c.has_track_correction, _cl.c.track_id,
        )
        if before_ts is not None and before_id is not None:
            stmt = stmt.where(tuple_(_cl.c.unix_ts, _cl.c.id) < (before_ts, before_id))
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
                stmt = stmt.where(_cl.c.unix_ts <= anchor_ts)
            except ValueError:
                logger.warning("Invalid anchor_date format: %r", anchor_date)
        stmt = stmt.order_by(desc(_cl.c.unix_ts), desc(_cl.c.id)).limit(limit)
        rows = conn.execute(stmt).all()
        return [
            ListenEntry(
                id=r.id, artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                source=r.source, duration_secs=r.duration_secs, album=r.album,
                recording_mbid=r.recording_mbid,
                has_listen_correction=bool(r.has_listen_correction),
                has_track_correction=bool(r.has_track_correction),
                track_id=r.track_id,
            )
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
    month_expr = get_month_num_expr(_cl.c.unix_ts)
    day_expr = get_day_num_expr(_cl.c.unix_ts)
    year_expr = get_year_expr(_cl.c.unix_ts)
    current_year = datetime.now().year

    with get_engine().connect() as conn:
        stmt = (
            select(
                _cl.c.id, _cl.c.artist, _cl.c.title, _cl.c.unix_ts, _cl.c.source,
                _cl.c.duration_secs, _cl.c.album, _cl.c.recording_mbid,
                _cl.c.has_listen_correction, _cl.c.has_track_correction, _cl.c.track_id,
                year_expr.label("year"),
            )
            .where(month_expr == month, day_expr == day)
            .order_by(desc(_cl.c.unix_ts))
        )
        rows = conn.execute(stmt).all()

    groups: dict[str, list[ListenEntry]] = {}
    for r in rows:
        if int(r.year) == current_year:
            continue
        groups.setdefault(str(r.year), []).append(
            ListenEntry(
                id=r.id, artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                source=r.source, duration_secs=r.duration_secs, album=r.album,
                recording_mbid=r.recording_mbid,
                has_listen_correction=bool(r.has_listen_correction),
                has_track_correction=bool(r.has_track_correction),
                track_id=r.track_id,
            )
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
    date_expr = get_date_expr(_cl.c.unix_ts)
    with get_engine().connect() as conn:
        stmt = (
            select(
                _cl.c.id, _cl.c.artist, _cl.c.title, _cl.c.unix_ts,
                _cl.c.source, _cl.c.duration_secs, _cl.c.album, _cl.c.recording_mbid,
                _cl.c.has_listen_correction, _cl.c.has_track_correction, _cl.c.track_id,
            )
            .where(date_expr == date_str)
            .order_by(_cl.c.unix_ts.asc(), _cl.c.id.asc())
        )
        rows = conn.execute(stmt).all()
        return [
            ListenEntry(
                id=r.id, artist=r.artist, title=r.title, unix_ts=r.unix_ts,
                source=r.source, duration_secs=r.duration_secs, album=r.album,
                recording_mbid=r.recording_mbid,
                has_listen_correction=bool(r.has_listen_correction),
                has_track_correction=bool(r.has_track_correction),
                track_id=r.track_id,
            )
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
    # Compute cutoff as a plain int so it works with _cl.c.unix_ts (corrected_listens view)
    range_cutoff: Optional[int] = None
    if time_range and time_range != "all":
        try:
            range_cutoff = int(datetime.now(timezone.utc).timestamp()) - (int(time_range) * 86400)
        except ValueError:
            pass

    artist_filter = func.lower(_cl.c.artist) == artist.lower()
    filters = [artist_filter]
    if range_cutoff is not None:
        filters.append(_cl.c.unix_ts >= range_cutoff)

    with get_engine().connect() as conn:
        total_plays = conn.execute(
            select(func.count(_cl.c.id)).where(*filters)
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

        # All-time rank (ignores time_range) — uses raw listens for global consistency
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

        total_track_count = conn.execute(
            select(func.count(distinct(_cl.c.title))).where(*filters)
        ).scalar() or 0

        # All tracks in selected time range — uses corrected_listens so corrections show in ArtistView
        stmt_tracks = (
            select(
                _cl.c.title,
                func.count(_cl.c.id).label("play_count"),
                func.min(_cl.c.unix_ts).label("first_ts"),
                func.max(_cl.c.unix_ts).label("last_ts"),
                func.max(_cl.c.album).label("album"),
                func.max(_cl.c.duration_secs).label("duration_secs"),
            )
            .where(*filters)
            .group_by(_cl.c.title)
            .order_by(desc("play_count"))
        )
        track_rows = conn.execute(stmt_tracks).all()

        # Batch-fetch a representative listen id per track (for the edit drawer)
        if track_rows:
            rep_rows = conn.execute(
                text("""
                    SELECT title, MAX(id) AS rep_id FROM listens
                    WHERE LOWER(artist) = LOWER(:artist)
                    GROUP BY title
                """),
                {"artist": artist},
            ).fetchall()
            rep_id_by_title = {r.title: r.rep_id for r in rep_rows}
        else:
            rep_id_by_title = {}

        top_tracks = [
            ArtistTopTrack(
                title=r.title, play_count=r.play_count,
                first_listen_ts=r.first_ts, last_listen_ts=r.last_ts,
                album=r.album, duration_secs=r.duration_secs,
                representative_listen_id=rep_id_by_title.get(r.title),
            )
            for r in track_rows
        ]

        # Monthly trends in selected time range
        month_expr = get_month_expr(_cl.c.unix_ts)
        stmt_monthly = (
            select(month_expr.label("month"), func.count(_cl.c.id).label("cnt"))
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
        date_expr = get_date_expr(_cl.c.unix_ts)
        stmt_peak = (
            select(date_expr.label("day"), func.count(_cl.c.id).label("cnt"))
            .where(*filters)
            .group_by(date_expr)
            .order_by(desc("cnt"))
            .limit(1)
        )
        day_row = conn.execute(stmt_peak).first()
        peak_day = WrappedPeakDay(date=day_row.day, plays=day_row.cnt) if day_row else None

        # Hourly distribution in selected time range
        hour_expr = get_hour_expr(_cl.c.unix_ts)
        stmt_hourly = (
            select(hour_expr.label("hour"), func.count(_cl.c.id).label("cnt"))
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
            select(func.min(_cl.c.unix_ts), func.count(_cl.c.id))
            .where(func.lower(_cl.c.artist) == artist.lower())
        ).first()
        first_listen_ts = all_time_row[0] if all_time_row else None
        plays_since_discovery = all_time_row[1] if all_time_row else 0

    return ArtistStatsResponse(
        artist=artist,
        total_plays=total_plays,
        total_track_count=total_track_count,
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


# ---------------------------------------------------------------------------
# Correction helpers
# ---------------------------------------------------------------------------


def get_listen_by_id(listen_id: int) -> Optional[ListenEntry]:
    """Fetch a single raw listen by primary key (bypasses corrected_listens view).

    Used by LB write-back to read the original values before they're overridden.
    Returns None if not found.
    """
    with get_engine().connect() as conn:
        row = conn.execute(
            select(
                Listen.id, Listen.artist, Listen.title, Listen.unix_ts,
                Listen.source, Listen.duration_secs, Listen.album, Listen.recording_mbid,
            ).where(Listen.id == listen_id)
        ).first()
    if not row:
        return None
    return ListenEntry(
        id=row.id, artist=row.artist, title=row.title, unix_ts=row.unix_ts,
        source=row.source, duration_secs=row.duration_secs, album=row.album,
        recording_mbid=row.recording_mbid,
    )


def get_listen_with_originals(listen_id: int) -> Optional[ListenEntry]:
    """Return the effective (corrected) listen alongside its raw original values.

    Populates has_listen_correction, has_track_correction, track_id, and
    original_* fields so the UI can show what was corrected and offer reverts.
    """
    with get_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    cl.id, cl.unix_ts, cl.source,
                    cl.artist, cl.title, cl.album, cl.duration_secs, cl.recording_mbid,
                    cl.has_listen_correction, cl.has_track_correction, cl.track_id,
                    l.artist  AS original_artist,
                    l.title   AS original_title,
                    l.album   AS original_album,
                    l.duration_secs AS original_duration_secs,
                    l.recording_mbid AS original_recording_mbid,
                    (SELECT COUNT(*) FROM corrected_listens cl2
                     WHERE LOWER(cl2.artist) = LOWER(cl.artist)
                       AND LOWER(cl2.title)  = LOWER(cl.title)) AS track_play_count,
                    CASE WHEN cac.manual_override THEN cac.original_url END AS original_cover_art_url
                FROM corrected_listens cl
                JOIN listens l ON l.id = cl.id
                LEFT JOIN cover_art_cache cac
                    ON cac.artist_folded = LOWER(TRIM(cl.artist))
                   AND cac.title_folded  = LOWER(TRIM(cl.title))
                WHERE cl.id = :id
            """),
            {"id": listen_id},
        ).first()
    if not row:
        return None
    any_correction = bool(row.has_listen_correction) or bool(row.has_track_correction)
    return ListenEntry(
        id=row.id, unix_ts=row.unix_ts, source=row.source,
        artist=row.artist, title=row.title, album=row.album,
        duration_secs=row.duration_secs, recording_mbid=row.recording_mbid,
        has_listen_correction=bool(row.has_listen_correction),
        has_track_correction=bool(row.has_track_correction),
        track_id=row.track_id,
        track_play_count=row.track_play_count,
        original_artist=row.original_artist if any_correction else None,
        original_title=row.original_title if any_correction else None,
        original_album=row.original_album if any_correction else None,
        original_duration_secs=row.original_duration_secs if any_correction else None,
        original_recording_mbid=row.original_recording_mbid if any_correction else None,
        original_cover_art_url=row.original_cover_art_url,
    )


def save_listen_correction(listen_id: int, corrections: dict[str, Any]) -> None:
    """Upsert a per-listen correction (wide schema).

    Keys in corrections must be a subset of: artist, title, album, duration_secs,
    recording_mbid. Pass "" (empty string) to explicitly clear a text field — do NOT
    convert "" to None before calling, since COALESCE("", x) returns "" (correct)
    while COALESCE(None, x) falls through (wrong).
    """
    fields = ["artist", "title", "album", "duration_secs", "recording_mbid"]
    params: dict[str, Any] = {"listen_id": listen_id}
    for f in fields:
        params[f] = corrections.get(f)  # None = don't touch this field

    with get_engine().begin() as conn:
        if IS_POSTGRES:
            conn.execute(
                text("""
                    INSERT INTO listen_corrections
                        (listen_id, artist, title, album, duration_secs, recording_mbid)
                    VALUES
                        (:listen_id, :artist, :title, :album, :duration_secs, :recording_mbid)
                    ON CONFLICT (listen_id) DO UPDATE SET
                        artist         = COALESCE(EXCLUDED.artist,         listen_corrections.artist),
                        title          = COALESCE(EXCLUDED.title,          listen_corrections.title),
                        album          = COALESCE(EXCLUDED.album,          listen_corrections.album),
                        duration_secs  = COALESCE(EXCLUDED.duration_secs,  listen_corrections.duration_secs),
                        recording_mbid = COALESCE(EXCLUDED.recording_mbid, listen_corrections.recording_mbid),
                        corrected_at   = now()
                """),
                params,
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO listen_corrections
                        (listen_id, artist, title, album, duration_secs, recording_mbid)
                    VALUES
                        (:listen_id, :artist, :title, :album, :duration_secs, :recording_mbid)
                    ON CONFLICT (listen_id) DO UPDATE SET
                        artist         = COALESCE(EXCLUDED.artist,         listen_corrections.artist),
                        title          = COALESCE(EXCLUDED.title,          listen_corrections.title),
                        album          = COALESCE(EXCLUDED.album,          listen_corrections.album),
                        duration_secs  = COALESCE(EXCLUDED.duration_secs,  listen_corrections.duration_secs),
                        recording_mbid = COALESCE(EXCLUDED.recording_mbid, listen_corrections.recording_mbid),
                        corrected_at   = strftime('%Y-%m-%d %H:%M:%S', 'now')
                """),
                params,
            )


def delete_listen(listen_id: int) -> None:
    """Permanently delete a listen and its correction (if any) from the local DB."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM listen_corrections WHERE listen_id = :id"), {"id": listen_id})
        conn.execute(text("DELETE FROM listens WHERE id = :id"), {"id": listen_id})


def get_track_listens(artist: str, title: str) -> List[ListenEntry]:
    """Return all individual listens for a corrected (artist, title) pair, newest first."""
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    cl.id, cl.unix_ts, cl.source,
                    cl.artist, cl.title, cl.album, cl.duration_secs, cl.recording_mbid,
                    cl.has_listen_correction, cl.has_track_correction, cl.track_id,
                    l.artist  AS original_artist,
                    l.title   AS original_title,
                    l.album   AS original_album,
                    l.duration_secs AS original_duration_secs,
                    l.recording_mbid AS original_recording_mbid
                FROM corrected_listens cl
                JOIN listens l ON l.id = cl.id
                WHERE LOWER(cl.artist) = LOWER(:artist) AND LOWER(cl.title) = LOWER(:title)
                ORDER BY cl.unix_ts DESC
            """),
            {"artist": artist, "title": title},
        ).fetchall()
    return [
        ListenEntry(
            id=r.id, unix_ts=r.unix_ts, source=r.source,
            artist=r.artist, title=r.title, album=r.album,
            duration_secs=r.duration_secs, recording_mbid=r.recording_mbid,
            has_listen_correction=bool(r.has_listen_correction),
            has_track_correction=bool(r.has_track_correction),
            track_id=r.track_id,
            original_artist=r.original_artist if (r.has_listen_correction or r.has_track_correction) else None,
            original_title=r.original_title if (r.has_listen_correction or r.has_track_correction) else None,
            original_album=r.original_album if (r.has_listen_correction or r.has_track_correction) else None,
            original_duration_secs=r.original_duration_secs if (r.has_listen_correction or r.has_track_correction) else None,
            original_recording_mbid=r.original_recording_mbid if (r.has_listen_correction or r.has_track_correction) else None,
        )
        for r in rows
    ]


def delete_track_listens(artist: str, title: str) -> int:
    """Delete all listens for a corrected (artist, title) pair. Returns count deleted."""
    with get_engine().begin() as conn:
        ids = [
            r[0] for r in conn.execute(
                text("SELECT id FROM corrected_listens WHERE LOWER(artist) = LOWER(:a) AND LOWER(title) = LOWER(:t)"),
                {"a": artist, "t": title},
            ).fetchall()
        ]
        if not ids:
            return 0
        id_list = ",".join(str(i) for i in ids)
        conn.execute(text(f"DELETE FROM listen_corrections WHERE listen_id IN ({id_list})"))
        conn.execute(text(f"DELETE FROM listens WHERE id IN ({id_list})"))
        # Clean up orphaned track_raw_keys and canonical_tracks
        conn.execute(text("""
            DELETE FROM track_raw_keys
            WHERE NOT EXISTS (
                SELECT 1 FROM listens
                WHERE listens.artist_raw_folded = track_raw_keys.artist_raw_folded
                  AND listens.title_raw_folded  = track_raw_keys.title_raw_folded
            )
        """))
        conn.execute(text("""
            DELETE FROM canonical_tracks
            WHERE NOT EXISTS (
                SELECT 1 FROM track_raw_keys WHERE track_raw_keys.canonical_track_id = canonical_tracks.id
            )
        """))
        return len(ids)


def delete_listen_correction(listen_id: int) -> None:
    """Delete the per-listen correction for a listen (revert to track correction or raw)."""
    with get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM listen_corrections WHERE listen_id = :id"),
            {"id": listen_id},
        )


def save_track_correction(
    corrected_artist: str,
    corrected_title: str,
    corrections: dict[str, Any],
    track_id: Optional[int] = None,
    recording_mbid: Optional[str] = None,
) -> Optional[int]:
    """Upsert a canonical track correction and map all matching raw keys to it.

    Lookup order: track_id → recording_mbid → artist/title fanout → create new.
    Returns the canonical_track_id.

    When no recording MBID is available, artist+title is treated as the best
    available approximation of logical track identity. Distinct recordings of the
    same title may be merged into one canonical_tracks row in that case.
    """
    ct_fields = {k: v for k, v in corrections.items()
                 if k in ("artist", "title", "album", "duration_secs", "recording_mbid")}
    new_mbid = ct_fields.get("recording_mbid") or recording_mbid

    with get_engine().begin() as conn:
        # --- Find or create the canonical_tracks row ---
        existing_id: Optional[int] = None

        if track_id is not None:
            row = conn.execute(
                text("SELECT id FROM canonical_tracks WHERE id = :id"),
                {"id": track_id},
            ).first()
            if row:
                existing_id = row.id

        if existing_id is None and new_mbid:
            row = conn.execute(
                text("SELECT id FROM canonical_tracks WHERE recording_mbid = :mbid"),
                {"mbid": new_mbid},
            ).first()
            if row:
                existing_id = row.id

        if existing_id is None:
            # Artist/title discovery: find if any existing canonical_track already maps
            # to the raw keys that currently resolve to corrected_artist/corrected_title.
            raw_key_row = conn.execute(
                text("""
                    SELECT trk.canonical_track_id
                    FROM corrected_listens cl
                    JOIN listens l ON l.id = cl.id
                    JOIN track_raw_keys trk
                        ON trk.artist_raw_folded = l.artist_raw_folded
                       AND trk.title_raw_folded  = l.title_raw_folded
                    WHERE cl.artist = :artist AND cl.title = :title
                    LIMIT 1
                """),
                {"artist": corrected_artist, "title": corrected_title},
            ).first()
            if raw_key_row:
                existing_id = raw_key_row.canonical_track_id

        if existing_id is not None:
            # Update existing canonical_tracks row
            set_parts = []
            update_params: dict[str, Any] = {"id": existing_id}
            for col in ("artist", "title", "album", "duration_secs", "recording_mbid"):
                if col in ct_fields:
                    set_parts.append(f"{col} = :{col}")
                    update_params[col] = ct_fields[col]
            if set_parts:
                if IS_POSTGRES:
                    set_parts.append("corrected_at = now()")
                else:
                    set_parts.append("corrected_at = strftime('%Y-%m-%d %H:%M:%S', 'now')")
                conn.execute(
                    text(f"UPDATE canonical_tracks SET {', '.join(set_parts)} WHERE id = :id"),
                    update_params,
                )
            canonical_track_id = existing_id
        else:
            # Create new canonical_tracks row
            ins_params: dict[str, Any] = {
                "artist": ct_fields.get("artist"),
                "title": ct_fields.get("title"),
                "album": ct_fields.get("album"),
                "duration_secs": ct_fields.get("duration_secs"),
                "recording_mbid": new_mbid,
            }
            if IS_POSTGRES:
                row = conn.execute(
                    text("""
                        INSERT INTO canonical_tracks
                            (artist, title, album, duration_secs, recording_mbid)
                        VALUES (:artist, :title, :album, :duration_secs, :recording_mbid)
                        RETURNING id
                    """),
                    ins_params,
                ).first()
                assert row is not None
                canonical_track_id = row.id
            else:
                conn.execute(
                    text("""
                        INSERT INTO canonical_tracks
                            (artist, title, album, duration_secs, recording_mbid)
                        VALUES (:artist, :title, :album, :duration_secs, :recording_mbid)
                    """),
                    ins_params,
                )
                canonical_track_id = conn.execute(
                    text("SELECT last_insert_rowid()")
                ).scalar()

        # --- Fan-out: upsert track_raw_keys for all matching raw identities ---
        raw_keys = conn.execute(
            text("""
                SELECT DISTINCT l.artist_raw_folded, l.title_raw_folded
                FROM corrected_listens cl
                JOIN listens l ON l.id = cl.id
                WHERE cl.artist = :artist AND cl.title = :title
            """),
            {"artist": corrected_artist, "title": corrected_title},
        ).fetchall()

        for rk in raw_keys:
            conn.execute(
                text("""
                    INSERT INTO track_raw_keys (canonical_track_id, artist_raw_folded, title_raw_folded)
                    VALUES (:ct_id, :af, :tf)
                    ON CONFLICT (artist_raw_folded, title_raw_folded)
                    DO UPDATE SET canonical_track_id = EXCLUDED.canonical_track_id
                """),
                {
                    "ct_id": canonical_track_id,
                    "af": rk.artist_raw_folded,
                    "tf": rk.title_raw_folded,
                },
            )

    return canonical_track_id


def delete_track_correction(
    corrected_artist: str,
    corrected_title: str,
    track_id: Optional[int] = None,
) -> None:
    """Delete the canonical track correction and its raw key mappings.

    If track_id is provided, deletes that row directly. Otherwise finds the
    canonical_track_id by querying corrected_listens for raw key matches.
    """
    with get_engine().begin() as conn:
        ct_id = track_id
        if ct_id is None:
            row = conn.execute(
                text("""
                    SELECT trk.canonical_track_id
                    FROM corrected_listens cl
                    JOIN listens l ON l.id = cl.id
                    JOIN track_raw_keys trk
                        ON trk.artist_raw_folded = l.artist_raw_folded
                       AND trk.title_raw_folded  = l.title_raw_folded
                    WHERE cl.artist = :artist AND cl.title = :title
                    LIMIT 1
                """),
                {"artist": corrected_artist, "title": corrected_title},
            ).first()
            if row:
                ct_id = row.canonical_track_id

        if ct_id is not None:
            conn.execute(
                text("DELETE FROM track_raw_keys WHERE canonical_track_id = :id"),
                {"id": ct_id},
            )
            conn.execute(
                text("DELETE FROM canonical_tracks WHERE id = :id"),
                {"id": ct_id},
            )


def get_corrected_play_count(corrected_artist: str, corrected_title: str) -> int:
    """Count listens that currently resolve to the given corrected artist+title."""
    with get_engine().connect() as conn:
        return conn.execute(
            text("""
                SELECT COUNT(*) FROM corrected_listens
                WHERE artist = :artist AND title = :title
            """),
            {"artist": corrected_artist, "title": corrected_title},
        ).scalar() or 0


def get_representative_listen_id(corrected_artist: str, corrected_title: str) -> Optional[int]:
    """Return the most-recent listen id that currently resolves to the given track."""
    with get_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT id FROM corrected_listens
                WHERE artist = :artist AND title = :title
                ORDER BY unix_ts DESC LIMIT 1
            """),
            {"artist": corrected_artist, "title": corrected_title},
        ).first()
    return row.id if row else None


def get_representative_listen_id_by_track_id(canonical_track_id: int) -> Optional[int]:
    """Return the most-recent listen id mapped to a canonical_track by its id.

    Used by revert endpoints to get a representative listen before deleting the
    canonical_tracks row (after which the raw-key join no longer resolves).
    """
    with get_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT l.id FROM listens l
                JOIN track_raw_keys trk
                    ON trk.artist_raw_folded = l.artist_raw_folded
                   AND trk.title_raw_folded  = l.title_raw_folded
                WHERE trk.canonical_track_id = :ct_id
                ORDER BY l.unix_ts DESC LIMIT 1
            """),
            {"ct_id": canonical_track_id},
        ).first()
    return row.id if row else None
