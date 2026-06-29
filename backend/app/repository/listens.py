from ._base import (
    Any,
    List,
    Optional,
    datetime,
    timezone,
    select,
    func,
    desc,
    and_,
    or_,
    text,
    tuple_,
    get_engine,
    Listen,
    _cl,
    logger,
    os,
    get_date_expr,
    get_month_num_expr,
    get_day_num_expr,
    get_year_expr,
    ArtistAnniversary,
    ListenEntry,
    OnThisDayGroup,
    OnThisDayResponse,
    TrackBatchResponseItem,
)
from .stats import get_time_range_filter


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
