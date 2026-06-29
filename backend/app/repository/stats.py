from ._base import (
    Optional,
    datetime,
    timezone,
    select,
    func,
    desc,
    distinct,
    or_,
    get_engine,
    Listen,
    IS_POSTGRES,
    get_date_expr,
    get_year_expr,
    StatsSummaryResponse,
    TopArtistsResponse,
    TopTracksResponse,
    ArtistInfo,
    TrackInfo,
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
