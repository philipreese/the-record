import logging
from datetime import datetime, date, timezone, timedelta
from typing import Any, List, Optional, cast
import os
from zoneinfo import ZoneInfo
from sqlalchemy import Boolean, Column, Integer, Table, Text, MetaData, select, func, desc, distinct, text, bindparam, tuple_, or_, and_
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
