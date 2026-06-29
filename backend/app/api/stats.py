from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query

import app.repository as repo
from app.narrative import generate_narrative
from app.schemas import (
    MonthlyTrendInfo,
    NarrativeResponse,
    StatsSummaryResponse,
    StreakStatsResponse,
    TopArtistsResponse,
    TopTracksResponse,
    WrappedDataResponse,
    WeeklyBreakdownItem,
)
from fastapi import Path

router = APIRouter()


@router.get("/stats", response_model=StatsSummaryResponse)
def read_stats() -> StatsSummaryResponse:
    return repo.get_stats_summary()


@router.get("/top-artists", response_model=TopArtistsResponse)
def read_top_artists(
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range"),
    limit: int = Query(15, ge=1, le=100),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
) -> TopArtistsResponse:
    actual_limit = page_size if page_size is not None else limit
    clean_search = search.strip() if search else None
    if clean_search == "":
        clean_search = None
    return repo.get_top_artists(time_range=range_param, limit=actual_limit, page=page, search=clean_search)


@router.get("/top-tracks", response_model=TopTracksResponse)
def read_top_tracks(
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range"),
    limit: int = Query(15, ge=1, le=100),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
) -> TopTracksResponse:
    actual_limit = page_size if page_size is not None else limit
    clean_search = search.strip() if search else None
    if clean_search == "":
        clean_search = None
    return repo.get_top_tracks(time_range=range_param, limit=actual_limit, page=page, search=clean_search)


@router.get("/heatmap", response_model=Dict[str, int])
def read_heatmap(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> dict[str, int]:
    return repo.get_heatmap_data(year=year)


@router.get("/trends/hourly", response_model=Dict[str, int])
def read_hourly_trends() -> dict[str, int]:
    return repo.get_hourly_trends()


@router.get("/trends/punchcard", response_model=Dict[str, int])
def read_punchcard() -> dict[str, int]:
    return repo.get_punchcard_data()


@router.get("/trends/monthly", response_model=List[MonthlyTrendInfo])
def read_monthly_trends() -> list[MonthlyTrendInfo]:
    return repo.get_monthly_trends()


@router.get("/trends/streak", response_model=StreakStatsResponse)
def read_streak() -> StreakStatsResponse:
    return repo.get_streak_stats()


@router.get("/trends/monthly/{year}/{month}/weekly", response_model=List[WeeklyBreakdownItem])
def read_monthly_weekly_breakdown(
    year: int = Path(..., ge=2000, le=2100),
    month: int = Path(..., ge=1, le=12),
) -> list[WeeklyBreakdownItem]:
    return repo.get_weekly_breakdown(year, month)


@router.get("/narrative", response_model=NarrativeResponse)
def read_narrative(
    seed: Optional[str] = Query(None),
) -> NarrativeResponse:
    stats = repo.get_stats_summary()
    streak = repo.get_streak_stats()
    return generate_narrative(stats, streak, seed)


@router.get("/wrapped", response_model=WrappedDataResponse)
def read_wrapped(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    quarter: Optional[Literal["Q1", "Q2", "Q3", "Q4"]] = Query(None),
    month: Optional[Literal["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"]] = Query(None),
) -> WrappedDataResponse:
    if not year:
        raise HTTPException(status_code=400, detail="You must specify a 'year' parameter.")
    return repo.get_wrapped_data(year=year, quarter=quarter, month=month)
