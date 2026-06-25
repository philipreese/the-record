from __future__ import annotations

from typing import Optional

import strawberry
import strawberry.experimental.pydantic as spydantic
from strawberry.fastapi import GraphQLRouter

import app.repository as repo
from app.schemas import ArtistMonthlyTrend, ArtistTopTrack, WrappedPeakDay


# Strawberry types derived from Pydantic models — no duplicate field declarations.
# from_pydantic() is injected by @spydantic.type at runtime; pyrefly: ignore suppresses
# the missing-attribute error on the three call sites below.

@spydantic.type(model=ArtistTopTrack, all_fields=True)
class ArtistTrack:
    pass


@spydantic.type(model=ArtistMonthlyTrend, all_fields=True)
class MonthlyTrend:
    pass


@spydantic.type(model=WrappedPeakDay, all_fields=True)
class PeakDay:
    pass


# Manual types — no corresponding Pydantic model.

@strawberry.type
class ArtistAlbum:
    name: str
    play_count: int


@strawberry.type
class HourlyCount:
    hour: str
    count: int


# Top-level result type — manual because it adds topAlbums (not in ArtistStatsResponse)
# and converts hourly dict → list.

@strawberry.type
class ArtistStats:
    artist: str
    total_plays: int
    rank: Optional[int]
    first_listen_ts: Optional[int]
    plays_since_discovery: Optional[int]
    top_tracks: list[ArtistTrack]
    top_albums: list[ArtistAlbum]
    monthly_trends: list[MonthlyTrend]
    peak_day: Optional[PeakDay]
    hourly: list[HourlyCount]


@strawberry.type
class Query:
    @strawberry.field
    def artist(self, name: str, time_range: str = "all") -> Optional[ArtistStats]:
        stats = repo.get_artist_stats(artist=name, time_range=time_range)
        if stats.total_plays == 0:
            return None

        # Derive top albums from tracks — aggregate play counts per album
        album_plays: dict[str, int] = {}
        for t in stats.top_tracks:
            if t.album:
                album_plays[t.album] = album_plays.get(t.album, 0) + t.play_count
        top_albums = [
            ArtistAlbum(name=a, play_count=p)
            for a, p in sorted(album_plays.items(), key=lambda x: -x[1])
        ]

        return ArtistStats(
            artist=stats.artist,
            total_plays=stats.total_plays,
            rank=stats.rank,
            first_listen_ts=stats.first_listen_ts,
            plays_since_discovery=stats.plays_since_discovery,
            top_tracks=[ArtistTrack.from_pydantic(t) for t in stats.top_tracks],  # pyrefly: ignore[missing-attribute]
            top_albums=top_albums,
            monthly_trends=[MonthlyTrend.from_pydantic(m) for m in stats.monthly_trends],  # pyrefly: ignore[missing-attribute]
            peak_day=PeakDay.from_pydantic(stats.peak_day) if stats.peak_day else None,  # pyrefly: ignore[missing-attribute]
            hourly=[HourlyCount(hour=h, count=c) for h, c in stats.hourly.items()],
        )


schema = strawberry.Schema(query=Query)
gql_router = GraphQLRouter(schema)
