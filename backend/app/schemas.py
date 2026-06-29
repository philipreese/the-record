from pydantic import BaseModel, model_validator
from typing import Any, Optional, List, Dict, Union

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
    recording_mbid: Optional[str] = None
    cover_art_url: Optional[str] = None
    # Correction metadata — populated by correction endpoints and list queries
    has_listen_correction: bool = False
    has_track_correction: bool = False
    track_id: Optional[int] = None
    # Original (raw) values — only set when at least one correction exists
    original_artist: Optional[str] = None
    original_title: Optional[str] = None
    original_album: Optional[str] = None
    original_duration_secs: Optional[int] = None
    original_recording_mbid: Optional[str] = None
    track_play_count: Optional[int] = None

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
    first_listen_ts: Optional[int] = None
    last_listen_ts: Optional[int] = None
    album: Optional[str] = None
    duration_secs: Optional[int] = None
    representative_listen_id: Optional[int] = None


class ArtistStatsResponse(BaseModel):
    artist: str
    total_plays: int
    rank: Optional[int] = None
    top_tracks: List[ArtistTopTrack]
    monthly_trends: List[ArtistMonthlyTrend]
    peak_day: Optional[WrappedPeakDay] = None
    hourly: Dict[str, int]
    first_listen_ts: Optional[int] = None
    plays_since_discovery: Optional[int] = None


class ArtistAnniversary(BaseModel):
    artist: str
    first_listen_ts: int
    years: int
    total_plays: int


class OnThisDayResponse(BaseModel):
    groups: List[OnThisDayGroup]
    anniversaries: List[ArtistAnniversary]


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


class ListenCorrectionRequest(BaseModel):
    artist: Optional[str] = None
    title: Optional[str] = None
    album: Optional[str] = None
    duration_secs: Optional[int] = None
    recording_mbid: Optional[str] = None
    cover_art_url: Optional[str] = None


class MBRecordingResult(BaseModel):
    mbid: str
    title: str
    artist_credit: str
    release: Optional[str] = None
    release_date: Optional[str] = None
    length_ms: Optional[int] = None
    release_mbid: Optional[str] = None


class MBSearchResponse(BaseModel):
    results: List[MBRecordingResult]


class TrackCorrectionRequest(BaseModel):
    track_id: Optional[int] = None
    corrected_artist: Optional[str] = None
    corrected_title: Optional[str] = None
    corrections: Dict[str, Optional[Union[str, int]]]

    @model_validator(mode="after")
    def validate_identity(self) -> "TrackCorrectionRequest":
        if self.track_id is not None:
            return self
        if self.corrected_artist and self.corrected_title:
            return self
        raise ValueError(
            "Either track_id or both corrected_artist+corrected_title are required."
        )


class TrackRevertRequest(BaseModel):
    track_id: Optional[int] = None
    corrected_artist: Optional[str] = None
    corrected_title: Optional[str] = None

    @model_validator(mode="after")
    def validate_identity(self) -> "TrackRevertRequest":
        if self.track_id is not None:
            return self
        if self.corrected_artist and self.corrected_title:
            return self
        raise ValueError(
            "Either track_id or both corrected_artist+corrected_title are required."
        )
