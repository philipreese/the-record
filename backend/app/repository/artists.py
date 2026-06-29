from ._base import (
    Optional,
    datetime,
    timezone,
    select,
    func,
    desc,
    distinct,
    text,
    get_engine,
    Listen,
    _cl,
    get_date_expr,
    get_hour_expr,
    get_month_expr,
    get_year_expr,
    ArtistMonthlyTrend,
    ArtistStatsResponse,
    ArtistTopTrack,
    ArtistTrendResponse,
    ArtistTrendSeries,
    TopArtistTrendsResponse,
    TrackMonthlyTrend,
    TrackTrendSeries,
    WrappedPeakDay,
)


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
