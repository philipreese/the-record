from ._base import (
    Optional,
    select,
    func,
    desc,
    get_engine,
    Listen,
    get_date_expr,
    get_year_expr,
    get_month_num_expr,
    WrappedDataResponse,
    WrappedArtist,
    WrappedTrack,
    WrappedPeakDay,
    OnRepeatPeak,
)


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
