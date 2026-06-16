# Data Models — The Record

> Part of the [modular specification](README.md).

## Listen (database entity)

The only persisted entity. All analytics are derived from this table.

```typescript
interface Listen {
  id: number;           // auto-increment primary key
  artist: string;       // indexed
  title: string;
  unix_ts: number;      // Unix timestamp, indexed
  source: string;       // "listenbrainz" | "listenbrainz_sync" | "youtube" | "google_takeout" | "unknown"
  duration_secs?: number | null;  // planned: #31 — populated from LB track_metadata.additional_info.duration_ms
  album?: string | null;          // planned: #31 — populated from LB track_metadata.release_name
}
```

**Source of truth:** [backend/app/db.py](../backend/app/db.py)

## Pydantic response schemas

**Source of truth:** [backend/app/schemas.py](../backend/app/schemas.py)

```typescript
interface StatsSummaryResponse {
  total_listens: number;
  unique_artists: number;
  unique_tracks: number;
  days_active: number;
  avg_per_day: number;
  top_source: string;
  db_type?: string;     // "sqlite" or "postgresql"
  first_year?: number;
}

interface ArtistInfo {
  artist: string;
  play_count: number;
}

interface TrackInfo {
  artist: string;
  title: string;
  play_count: number;
}

interface MonthlyTrendInfo {
  month: string;    // "YYYY-MM"
  count: number;
}

interface StreakStatsResponse {
  current_streak: number;   // consecutive days up to today
  longest_streak: number;
}

interface WrappedArtist {
  name: string;
  plays: number;
}

interface WrappedTrack {
  artist: string;
  title: string;
  plays: number;
}

interface WrappedPeakDay {
  date: string;   // "YYYY-MM-DD"
  plays: number;
}

interface WrappedDataResponse {
  total_plays: number;
  top_artist?: WrappedArtist;
  top_track?: WrappedTrack;
  peak_day?: WrappedPeakDay;
  minutes_listened: number;
}

interface TrackStatsResponse {
  play_count: number;
  duration_secs?: number | null;   // null until #31 (duration_secs migration) lands
}

interface SyncStartResponse {
  status: string;       // "started" | "already_running"
  mode?: string;
  message?: string;
}

interface SyncStatusResponse {
  running: boolean;
  finished: boolean;
  mode: string;
  batches_fetched: number;
  synced_count: number;
  lb_total: number;
  local_total: number;
  error?: string;
}
```

## Environment config

**Source of truth:** [backend/app/db.py](../backend/app/db.py), [backend/app/sync.py](../backend/app/sync.py), [backend/app/main.py](../backend/app/main.py)

| Variable                | Default                       | Purpose                                                                                                                                      |
| ----------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`          | _(unset)_                     | PostgreSQL connection string. If set, overrides SQLite. Schemes `postgres://` and `postgresql://` are normalized to `postgresql+psycopg://`. |
| `DATABASE_PATH`         | `backend/history.db`          | Path to SQLite file. Ignored when `DATABASE_URL` is set.                                                                                     |
| `JSON_PATH`             | `backend/merged_history.json` | Path to bootstrap JSON for initial DB population.                                                                                            |
| `TZ`                    | _(unset)_                     | Timezone applied to PostgreSQL sessions (`SET timezone=…`). No effect on SQLite.                                                             |
| `LISTENBRAINZ_USERNAME` | _(required for sync)_         | ListenBrainz account username.                                                                                                               |
| `LISTENBRAINZ_TOKEN`    | _(required for sync)_         | ListenBrainz user token.                                                                                                                     |
| `SYNC_TOKEN`            | _(required to enable sync)_   | Shared secret guarding `POST /api/sync`. Requests must send a matching `X-Sync-Token` header. If unset, the route fails closed with `503`. Set this in the Render service env. |
| `LOG_LEVEL`             | `INFO`                        | Python logging level for `app.*` loggers (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Set to `DEBUG` on Render when diagnosing issues. |
