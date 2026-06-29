from typing import Literal

from fastapi import APIRouter, HTTPException, Query

import app.repository as repo
from app.schemas import ArtistStatsResponse, ArtistTrendResponse, TopArtistTrendsResponse

router = APIRouter()


@router.get("/top-artist-trends", response_model=TopArtistTrendsResponse)
def read_top_artist_trends(
    year: int = Query(..., ge=2000, le=2100),
    limit: int = Query(5, ge=1, le=20),
) -> TopArtistTrendsResponse:
    return repo.get_top_artist_trends(year=year, limit=limit)


@router.get("/artist-trend", response_model=ArtistTrendResponse)
def read_artist_trend(
    artist: str = Query(...),
    year: int = Query(..., ge=2000, le=2100),
    limit: int = Query(5, ge=1, le=20),
) -> ArtistTrendResponse:
    clean_artist = artist.strip()
    if not clean_artist:
        raise HTTPException(status_code=400, detail="Artist name cannot be empty.")
    return repo.get_artist_track_trends(artist=clean_artist, year=year, limit=limit)


@router.get("/artist/stats", response_model=ArtistStatsResponse)
def read_artist_stats(
    name: str = Query(...),
    range_param: Literal["30", "90", "365", "all"] = Query("all", alias="range"),
) -> ArtistStatsResponse:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Artist name cannot be empty.")
    return repo.get_artist_stats(artist=clean_name, time_range=range_param)
