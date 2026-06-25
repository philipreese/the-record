from __future__ import annotations

from typing import Optional

import strawberry
from strawberry.fastapi import GraphQLRouter

import app.repository as repo


@strawberry.type
class ArtistTrack:
    title: str
    play_count: int
    album: Optional[str]
    duration_secs: Optional[int]
    first_listen_ts: Optional[int]
    last_listen_ts: Optional[int]


@strawberry.type
class ArtistAlbum:
    name: str
    play_count: int


@strawberry.type
class MonthlyTrend:
    month: str
    count: int


@strawberry.type
class HourlyCount:
    hour: str
    count: int


@strawberry.type
class PeakDay:
    date: str
    plays: int


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
            top_tracks=[
                ArtistTrack(
                    title=t.title,
                    play_count=t.play_count,
                    album=t.album,
                    duration_secs=t.duration_secs,
                    first_listen_ts=t.first_listen_ts,
                    last_listen_ts=t.last_listen_ts,
                )
                for t in stats.top_tracks
            ],
            top_albums=top_albums,
            monthly_trends=[
                MonthlyTrend(month=m.month, count=m.count)
                for m in stats.monthly_trends
            ],
            peak_day=PeakDay(date=stats.peak_day.date, plays=stats.peak_day.plays)
            if stats.peak_day
            else None,
            hourly=[
                HourlyCount(hour=h, count=c) for h, c in stats.hourly.items()
            ],
        )


schema = strawberry.Schema(query=Query)
gql_router = GraphQLRouter(schema)
