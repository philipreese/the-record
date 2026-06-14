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

class TrackInfo(BaseModel):
    artist: str
    title: str
    play_count: int

class ListenEntry(BaseModel):
    id: int
    artist: str
    title: str
    unix_ts: int
    source: str

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

class WrappedDataResponse(BaseModel):
    total_plays: int
    top_artist: Optional[WrappedArtist] = None
    top_track: Optional[WrappedTrack] = None
    peak_day: Optional[WrappedPeakDay] = None
    minutes_listened: int

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
    lb_total: int
    local_total: int
    error: Optional[str] = None
