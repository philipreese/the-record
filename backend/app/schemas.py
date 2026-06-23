from pydantic import BaseModel
from typing import Optional, List, Dict

class StatsSummaryResponse(BaseModel):
    total_listens: int
    unique_artists: int
    unique_tracks: int
    days_active: int
    avg_per_day: float
    top_source: str
    db_type: Optional[str] = None
    first_year: Optional[int] = None
class ArtistInfo(BaseModel):
    artist: str
    play_count: int
    rank: Optional[int] = None

class TopArtistsResponse(BaseModel):
    items: List[ArtistInfo]
    total_count: int

class TrackInfo(BaseModel):
    artist: str
    title: str
    play_count: int
    rank: Optional[int] = None

class TopTracksResponse(BaseModel):
    items: List[TrackInfo]
    total_count: int

class ListenEntry(BaseModel):
    id: int
    artist: str
    title: str
    unix_ts: int
    source: str
    duration_secs: Optional[int] = None
    album: Optional[str] = None

class MonthlyTrendInfo(BaseModel):
    month: str
    count: int

class StreakStatsResponse(BaseModel):
    current_streak: int
    longest_streak: int

class WrappedArtist(BaseModel):
    name: str
    plays: int

class WrappedTrack(BaseModel):
    artist: str
    title: str
    plays: int

class WrappedPeakDay(BaseModel):
    date: str
    plays: int

class OnRepeatPeak(BaseModel):
    artist: str
    title: str
    date: str    # YYYY-MM-DD
    count: int

class WrappedDataResponse(BaseModel):
    total_plays: int
    top_artist: Optional[WrappedArtist] = None
    top_track: Optional[WrappedTrack] = None
    peak_day: Optional[WrappedPeakDay] = None
    minutes_listened: int
    on_repeat_peak: Optional[OnRepeatPeak] = None

class SyncStartResponse(BaseModel):
    status: str
    mode: Optional[str] = None
    message: Optional[str] = None

class SyncStatusResponse(BaseModel):
    running: bool
    finished: bool
    mode: str
    batches_fetched: int
    synced_count: int
    updated_count: int
    deleted_count: int
    lb_total: int
    local_total: int
    error: Optional[str] = None

class LastPlayedEntry(BaseModel):
    artist: str
    title: str
    unix_ts: int
    cover_art_url: Optional[str] = None

class PlayingNowResponse(BaseModel):
    is_playing: bool
    artist: Optional[str] = None
    title: Optional[str] = None
    release: Optional[str] = None
    cover_art_url: Optional[str] = None
    last_played: Optional[LastPlayedEntry] = None

class TrackStatsResponse(BaseModel):
    play_count: int
    duration_secs: Optional[int] = None

class OnThisDayGroup(BaseModel):
    year: int
    listens: List[ListenEntry]

class TrackBatchRequestItem(BaseModel):
    artist: str
    title: str

class TrackBatchResponseItem(BaseModel):
    artist: str
    title: str
    play_count: int
    duration_secs: Optional[int] = None

class WeeklyBreakdownItem(BaseModel):
    week: int
    count: int


class NarrativeResponse(BaseModel):
    plain: Dict[str, str]
    rich: Dict[str, str]


class ArtistMonthlyTrend(BaseModel):
    month: str
    count: int


class ArtistTopTrack(BaseModel):
    title: str
    play_count: int


class ArtistStatsResponse(BaseModel):
    artist: str
    total_plays: int
    rank: Optional[int] = None
    top_tracks: List[ArtistTopTrack]
    monthly_trends: List[ArtistMonthlyTrend]
    peak_day: Optional[WrappedPeakDay] = None
    hourly: Dict[str, int]
    first_listen_ts: Optional[int] = None


class ArtistTrendSeries(BaseModel):
    artist: str
    play_count: int
    monthly_counts: List[ArtistMonthlyTrend]


class TopArtistTrendsResponse(BaseModel):
    year: int
    trends: List[ArtistTrendSeries]


class TrackMonthlyTrend(BaseModel):
    month: str
    count: int


class TrackTrendSeries(BaseModel):
    track: str
    play_count: int
    monthly_counts: List[TrackMonthlyTrend]


class ArtistTrendResponse(BaseModel):
    artist: str
    year: int
    trends: List[TrackTrendSeries]
