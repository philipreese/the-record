"""Repository package — re-exports every public function from domain submodules."""

from .cover_art import (
    get_all_cover_art,
    get_cover_art_batch,
    upsert_cover_art,
)
from .stats import (
    get_stats_summary,
    get_time_range_filter,
    get_top_artists,
    get_top_tracks,
)
from .trends import (
    get_heatmap_data,
    get_hourly_trends,
    get_punchcard_data,
    get_monthly_trends,
    get_streak_stats,
    get_weekly_breakdown,
)
from .wrapped import get_wrapped_data
from .listens import (
    get_recent_listens,
    get_track_stats,
    get_track_play_count,
    get_track_stats_batch,
    get_on_this_day_anniversaries,
    get_on_this_day,
    get_export_data,
    get_listens_by_day,
)
from .artists import (
    get_top_artist_trends,
    get_artist_stats,
    get_artist_track_trends,
)
from .corrections import (
    deduplicate_listens,
    apply_artist_corrections,
    get_listen_by_id,
    get_listen_with_originals,
    save_listen_correction,
    delete_listen,
    get_track_listens,
    delete_track_listens,
    delete_listen_correction,
    save_track_correction,
    delete_track_correction,
    get_corrected_play_count,
    get_representative_listen_id,
    get_representative_listen_id_by_track_id,
)
from ._base import get_current_local_date

__all__ = [
    # cover_art
    "get_all_cover_art",
    "get_cover_art_batch",
    "upsert_cover_art",
    # stats
    "get_stats_summary",
    "get_time_range_filter",
    "get_top_artists",
    "get_top_tracks",
    # trends
    "get_heatmap_data",
    "get_hourly_trends",
    "get_punchcard_data",
    "get_monthly_trends",
    "get_streak_stats",
    "get_weekly_breakdown",
    # wrapped
    "get_wrapped_data",
    # listens
    "get_recent_listens",
    "get_track_stats",
    "get_track_play_count",
    "get_track_stats_batch",
    "get_on_this_day_anniversaries",
    "get_on_this_day",
    "get_export_data",
    "get_listens_by_day",
    # artists
    "get_top_artist_trends",
    "get_artist_stats",
    "get_artist_track_trends",
    # corrections
    "deduplicate_listens",
    "apply_artist_corrections",
    "get_listen_by_id",
    "get_listen_with_originals",
    "save_listen_correction",
    "delete_listen",
    "get_track_listens",
    "delete_track_listens",
    "delete_listen_correction",
    "save_track_correction",
    "delete_track_correction",
    "get_corrected_play_count",
    "get_representative_listen_id",
    "get_representative_listen_id_by_track_id",
    # base
    "get_current_local_date",
]
