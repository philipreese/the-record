from ._base import (
    datetime,
    timedelta,
    select,
    func,
    desc,
    distinct,
    get_engine,
    Listen,
    get_date_expr,
    get_hour_expr,
    get_month_expr,
    get_day_num_expr,
    get_year_expr,
    get_day_of_week_expr,
    MonthlyTrendInfo,
    StreakStatsResponse,
    WeeklyBreakdownItem,
    get_current_local_date,
)


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
